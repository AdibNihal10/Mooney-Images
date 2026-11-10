import bpy
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
from pathlib import Path
import objaverse
import shutil

MODEL_DIR = Path('/models')
OUTPUT_DIR = Path('/output')
TARGET_MODELS = 20
model_uuid_files = []


def models_already_downloaded():
    model_dir = Path('/models/')  # mounted path for the container its different then the project
    model_files = list(model_dir.glob('*.glb'))
    model_uuid_files.clear()
    #extract the file names
    for file in model_files:
        model_uuid_files.append(file.stem)
    return len(model_files) - TARGET_MODELS


def model_metadata_ok(model):
    faces = model.get('faceCount')
    vertices = model.get('vertexCount')
    return (
        model.get('isDownloadable') is True
        and model.get('isAgeRestricted') is not True
        and (model.get('animationCount') or 0) == 0
        and isinstance(faces, (int, float)) and 1000 <= faces < 100000
        and isinstance(vertices, (int, float)) and vertices >= 500
    )


def download_models(count_of_models):
    categories = objaverse.load_lvis_annotations()
    selected_categories = list(categories.keys())[:20]
    selected_uuids = []

    for category in selected_categories:
        # Skip category if we already downloaded a model from it
        if any(uid in model_uuid_files for uid in categories[category]):
            continue
        for uuid in categories[category]:
            model = objaverse.load_annotations([uuid]).get(uuid, {})
            if model_metadata_ok(model):
                selected_uuids.append(uuid)
                break
        # Stop once we've selected enough new models
        if len(selected_uuids) >= count_of_models:
            break

    if not selected_uuids:
        return
    models = objaverse.load_objects(uids=selected_uuids)
    for uid, source_path in models.items():
        source = Path(source_path)
        if source.is_file() and source.suffix.lower() == '.glb':
            destination = MODEL_DIR / f'{uid}.glb'
            shutil.copy2(source, destination)


def setup_camera():
    bpy.ops.object.camera_add(location=(0, -8, 5))
    camera = bpy.context.object
    target = Vector((0, 0, 0))
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = camera
    return camera


def import_model(uuid):
    model_path = Path('/models') / f'{uuid}.glb'
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(model_path))
    return list(set(bpy.data.objects) - before)


def mesh_corners(imported_objects):
    corners = []
    for obj in imported_objects:
        if obj.type == 'MESH':
            corners.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    return corners


def normalize_model(imported_objects):
    """Center model geometry at the origin; normalize its longest dimension to 2 units."""
    bpy.context.view_layer.update()
    corners = mesh_corners(imported_objects)
    if not corners:
        return False
    low = Vector([min(point[i] for point in corners) for i in range(3)])
    high = Vector([max(point[i] for point in corners) for i in range(3)])
    dimensions = high - low
    longest = max(dimensions)
    shortest = min(dimensions)
    if longest <= 1e-6 or shortest / longest < 0.01:
        return False
    center = (low + high) / 2
    transform = Matrix.Scale(2.0 / longest, 4) @ Matrix.Translation(-center)
    imported = set(imported_objects)
    # Transform only top-level objects: children follow their parents.
    for obj in imported_objects:
        if obj.parent not in imported:
            obj.matrix_world = transform @ obj.matrix_world
    bpy.context.view_layer.update()
    return True


def frame_camera(camera, imported_objects):
    """Preserve the same viewing direction; change camera distance to fit the object."""
    corners = mesh_corners(imported_objects)
    if not corners:
        return False
    direction = Vector((0, -8, 5)).normalized()
    distance = 4.5
    scene = bpy.context.scene
    for _ in range(20):
        camera.location = direction * distance
        camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        coords = [world_to_camera_view(scene, camera, point) for point in corners]
        if any(point.z <= 0 for point in coords):
            distance *= 1.5
            continue
        min_x, max_x = min(p.x for p in coords), max(p.x for p in coords)
        min_y, max_y = min(p.y for p in coords), max(p.y for p in coords)
        width, height = max_x - min_x, max_y - min_y
        if (
            0.10 <= min_x and max_x <= 0.90
            and 0.10 <= min_y and max_y <= 0.90
            and width >= 0.25 and height >= 0.25
        ):
            return True
        if width < 0.25 or height < 0.25:
            # An extreme aspect ratio may never satisfy both thresholds.
            if width / max(height, 1e-9) < 0.33 or height / max(width, 1e-9) < 0.33:
                return False
        # Adjust distance according to the largest projected dimension.
        size = max(width, height)
        distance *= max(0.5, min(1.8, size / 0.70))
    return False


# adding light positions leaving bottom
light_positions = [
    (-5, 0, 5),
    (5, 0, 5),
    (0, -5, 5),
    (0, 5, 5),
    (0, 0, 8)
]


def setup_light():
    bpy.ops.object.light_add(type='POINT', location=light_positions[0])
    light = bpy.context.object
    light.data.energy = 1000
    light.data.shadow_soft_size = 0.05
    return light


def render_five_images(uuid, light):
    for i, position in enumerate(light_positions):
        light.location = position
        bpy.context.scene.render.filepath = f'/output/{uuid}_{i}.png'
        bpy.ops.render.render(write_still=True)


def remove_model(imported_objects):
    # Remove everything imported by glTF, including empties and armatures.
    for obj in imported_objects:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # download the objects that needs to be modelled through Objaverse
    # do check if we already have them
    model_count = models_already_downloaded()
    if model_count < 0:
        download_models(abs(model_count))

    # once the models are downloaded in the /data/models count should be 20
    # we need to setup the camera and lighting for photo session -> say "cheese"
    # Clear Blender's default cube, camera, and light before controlled rendering.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.world.color = (0, 0, 0)
    camera = setup_camera()
    light = setup_light()

    # let's call in the models
    all_uuids = [file.stem for file in Path('/models').glob('*.glb')]
    accepted = 0
    for uuid in all_uuids:
        imported_objects = import_model(uuid)
        try:
            if not normalize_model(imported_objects):
                print(f'SKIP {uuid}: invalid or extreme geometry')
                continue
            if not frame_camera(camera, imported_objects):
                print(f'SKIP {uuid}: camera framing failed')
                continue
            # pay 1 euro cause i am a broke student
            render_five_images(uuid, light)
            accepted += 1
        finally:
            # if the model doesn't accept 1 euro payment then kick them out
            remove_model(imported_objects)
    print(f'Rendered {accepted} models, {accepted * 5} images')
    if accepted != TARGET_MODELS:
        print('WARNING: Fewer than 20 models passed validation. Replace rejected candidates.')


if __name__ == '__main__':
    main()
