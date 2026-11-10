import bpy
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
from pathlib import Path
from array import array
import objaverse
import shutil
import json
import math
import re

MODEL_DIR = Path('/models')
OUTPUT_DIR = Path('/output')
TARGET_MODELS = 20
MAX_CANDIDATES_PER_CATEGORY = 40
PIPELINE_VERSION = "mooney-curated-v3-2026-11-10"
model_uuid_files = []

# Prefer recognizable, geometrically distinct objects over arbitrary first categories.
# Names are matched against the available Objaverse-LVIS category keys.
PREFERRED_CATEGORIES = [
    # Objects with a generally recognizable 3D shape rather than a label or texture.
    'airplane', 'chair', 'bicycle', 'guitar', 'backpack',
    'bottle', 'teapot', 'suitcase', 'camera', 'alarm_clock',
    'shoe', 'umbrella', 'bus', 'boat', 'dog', 'apple', 'banana',
    'motorcycle', 'mug', 'lamp', 'helicopter', 'train',
    'telephone', 'truck', 'violin', 'elephant', 'toaster', 'hat',
    'clock', 'laptop', 'ambulance', 'alligator', 'car',
    'rocket', 'scissors', 'piano', 'stapler', 'watering_can',
    'fire_extinguisher', 'teddy_bear', 'horse', 'duck', 'bed',
    'sofa', 'skateboard', 'tractor', 'fork', 'air_conditioner',
]
# Do not select categories just because they sort first alphabetically.
# The previous ZIP included a boat labelled "Band_Aid", and shape-poor
# candidates such as an anklet, almond, and a flat "alcohol" model.



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
        and model.get('license') in {'by', 'by-sa', 'cc0'}
        and (model.get('animationCount') or 0) == 0
        and isinstance(faces, (int, float)) and 800 <= faces < 100000
        and isinstance(vertices, (int, float)) and vertices >= 500
    )



def model_label_ok(category, metadata):
    """Reject obvious semantic mismatches before spending time on rendering.

    LVIS group membership is not enough: the previous Band_Aid model was a boat.
    Name/tags are imperfect proxies for meaning, not a semantic guarantee.
    """
    aliases = {
        'airplane': ('airplane', 'aeroplane', 'aircraft', 'plane', 'jet'),
        'alarm_clock': ('alarm clock', 'alarm_clock'),
        'bicycle': ('bicycle', 'bike', 'cycle'),
        'car': ('car', 'automobile', 'sedan', 'coupe'),
        'bus': ('bus', 'coach'),
        'boat': ('boat', 'ship', 'vessel'),
        'motorcycle': ('motorcycle', 'motorbike', 'motor bike'),
        'shoe': ('shoe', 'sneaker', 'boot', 'trainer'),
        'camera': ('camera', 'dslr'),
        'telephone': ('telephone', 'phone', 'handset'),
        'lamp': ('lamp', 'lantern'),
        'mug': ('mug', 'cup'),
        'umbrella': ('umbrella', 'parasol'),
        'teddy_bear': ('teddy', 'bear'),
        'fire_extinguisher': ('fire extinguisher', 'extinguisher'),
    }
    normalized = category.lower().replace('_', ' ')
    terms = aliases.get(category.lower(), (normalized,))
    name = (metadata.get('name') or '').lower()
    tags = metadata.get('tags') or []
    tag_names = []
    for tag in tags:
        if isinstance(tag, dict):
            tag_names.append(str(tag.get('name', '')))
        elif isinstance(tag, str):
            tag_names.append(tag)
    searchable = ' '.join([name] + tag_names).lower().replace('_', ' ')
    return any(re.search(r'(?<![a-z0-9])' + re.escape(term.replace('_', ' ')) + r'(?![a-z0-9])', searchable)
               for term in terms)

def download_models(count_of_models):
    """Compatibility helper; main() selects and validates candidates before saving."""
    categories = objaverse.load_lvis_annotations()
    selected_categories = list(categories.keys())[:20]
    selected_uuids = []
    for category in selected_categories:
        # Skip category if we already downloaded a model from it
        if any(uid in model_uuid_files for uid in categories[category]):
            continue
        ids = categories[category][:MAX_CANDIDATES_PER_CATEGORY]
        annotations = objaverse.load_annotations(ids)
        for uuid in ids:
            if model_metadata_ok(annotations.get(uuid, {})):
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
    camera.data.clip_end = 1000
    bpy.context.scene.camera = camera
    return camera


def import_model(uuid, path=None):
    model_path = Path(path) if path is not None else MODEL_DIR / f'{uuid}.glb'
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(model_path))
    imported = list(set(bpy.data.objects) - before)
    # Imported GLBs may contain cameras and lights: do not let them change our experiment.
    for obj in list(imported):
        if obj.type in {'LIGHT', 'CAMERA'}:
            bpy.data.objects.remove(obj, do_unlink=True)
            imported.remove(obj)
    return imported


def mesh_corners(imported_objects):
    corners = []
    for obj in imported_objects:
        if obj.type == 'MESH' and obj.name in bpy.data.objects and len(obj.data.vertices) > 0:
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
    if not math.isfinite(longest) or longest <= 1e-6 or shortest / longest < 0.035:
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
    """Keep the viewing direction fixed, fit the object, and leave a 10% margin."""
    corners = mesh_corners(imported_objects)
    if not corners:
        return False
    direction = Vector((0, -8, 5)).normalized()
    scene = bpy.context.scene

    def fits(distance):
        camera.location = direction * distance
        camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        coords = [world_to_camera_view(scene, camera, point) for point in corners]
        return all(math.isfinite(p.x) and math.isfinite(p.y) and math.isfinite(p.z)
                   and p.z > 0 and 0.10 <= p.x <= 0.90 and 0.10 <= p.y <= 0.90
                   for p in coords)

    # Grow the distance until the entire object is within the frame.
    high = 4.5
    for _ in range(24):
        if fits(high):
            break
        high *= 1.5
    else:
        return False
    # Then approach the object for the tightest framing with a 10% margin.
    low = 0.01
    for _ in range(25):
        mid = (low + high) / 2
        if fits(mid):
            high = mid
        else:
            low = mid
    return fits(high)


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
    light.name = 'MovingKeyLight'
    light.data.energy = 1400
    light.data.shadow_soft_size = 0.08
    # A fixed low-power fill prevents the object disappearing into black on one side.
    bpy.ops.object.light_add(type='POINT', location=(0, -5, 4))
    fill = bpy.context.object
    fill.name = 'FixedFillLight'
    fill.data.energy = 650
    fill.data.shadow_soft_size = 1.0
    return light


def setup_neutral_material():
    """Use the same matte gray for every model; no textures, logos or shininess."""
    material = bpy.data.materials.new('DatasetNeutralMatte')
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (0.80, 0.80, 0.80, 1)
    bsdf.inputs['Roughness'].default_value = 1.0
    bsdf.inputs['Metallic'].default_value = 0.0
    return material


def apply_neutral_material(imported_objects, material):
    for obj in imported_objects:
        if obj.type == 'MESH':
            obj.data.materials.clear()
            obj.data.materials.append(material)


def preview_usable(uuid, light):
    """Reject candidates that render too small, nearly black, or invisible.

    Evaluate all five lighting positions; a single bright frontal preview is
    insufficient for this lighting-direction experiment.
    """
    scene = bpy.context.scene
    old_x, old_y = scene.render.resolution_x, scene.render.resolution_y
    old_transparent = scene.render.film_transparent
    old_color_mode = scene.render.image_settings.color_mode
    old_path = scene.render.filepath
    old_light_location = light.location.copy()
    preview_path = OUTPUT_DIR / f'__preview_{uuid}.png'
    try:
        scene.render.resolution_x = 128
        scene.render.resolution_y = 128
        scene.render.film_transparent = True
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.filepath = str(preview_path)
        coverages = []
        brightnesses = []
        for position in light_positions:
            # Keep the same light power and distance for fair comparisons.
            light.location = Vector(position).normalized() * 7.0
            bpy.ops.render.render(write_still=True)
            image = bpy.data.images.load(str(preview_path), check_existing=False)
            try:
                pixels = array('f', [0.0]) * len(image.pixels)
                image.pixels.foreach_get(pixels)
            finally:
                bpy.data.images.remove(image)
            total = len(pixels) // 4
            occupied = 0
            luminance_sum = 0.0
            bright_pixels = 0
            for j in range(0, len(pixels), 4):
                alpha = pixels[j + 3]
                if alpha > 0.5:
                    occupied += 1
                    luminance = (pixels[j] + pixels[j+1] + pixels[j+2]) / 3.0
                    luminance_sum += luminance
                    if luminance > 0.075:
                        bright_pixels += 1
            coverage = occupied / max(total, 1)
            average_brightness = luminance_sum / max(occupied, 1)
            bright_fraction = bright_pixels / max(occupied, 1)
            coverages.append(coverage)
            brightnesses.append(average_brightness)
            if not (0.065 <= coverage <= 0.72 and average_brightness >= 0.09
                    and bright_fraction >= 0.40):
                print(f'SKIP {uuid}: preview quality coverage={coverage:.3f}, '
                      f'brightness={average_brightness:.3f}, lit={bright_fraction:.3f}')
                return False
        print(f'PREVIEW {uuid}: coverage={min(coverages):.3f}, '
              f'min_brightness={min(brightnesses):.3f}')
        # Calibration thresholds; these cannot establish semantic recognizability.
        return True
    finally:
        preview_path.unlink(missing_ok=True)
        scene.render.resolution_x, scene.render.resolution_y = old_x, old_y
        scene.render.film_transparent = old_transparent
        scene.render.image_settings.color_mode = old_color_mode
        scene.render.filepath = old_path
        light.location = old_light_location


def render_five_images(uuid, light):
    paths = []
    try:
        for i, position in enumerate(light_positions):
            light.location = position
            # Equalize key-light distance to keep direction as the primary changing factor.
            light.location = Vector(position).normalized() * 7.0
            path = OUTPUT_DIR / f'{uuid}_{i}.png'
            # Don't mistake an old PNG for a newly successful render.
            path.unlink(missing_ok=True)
            bpy.context.scene.render.filepath = str(path)
            bpy.ops.render.render(write_still=True)
            if not path.is_file() or path.stat().st_size == 0:
                raise RuntimeError(f'Render not saved: {path}')
            paths.append(path)
    except Exception:
        # Avoid leaving incomplete 1-4 image sets behind.
        for path in paths:
            path.unlink(missing_ok=True)
        raise


def remove_model(imported_objects):
    # Remove everything imported by glTF, including empties and armatures.
    for obj in imported_objects:
        if obj.name in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)


def try_candidate(uuid, path, camera, light, material):
    """Render only after geometry, camera, and silhouette checks succeed."""
    before = set(bpy.data.objects)
    try:
        imported_objects = import_model(uuid, path)
        if not normalize_model(imported_objects):
            print(f'SKIP {uuid}: invalid or extreme geometry')
            return False
        apply_neutral_material(imported_objects, material)
        if not frame_camera(camera, imported_objects):
            print(f'SKIP {uuid}: camera framing failed')
            return False
        if not preview_usable(uuid, light):
            print(f'SKIP {uuid}: silhouette/lighting preview failed')
            return False
        # pay 1 euro cause i am a broke student
        render_five_images(uuid, light)
        return True
    except Exception as exc:
        print(f'SKIP {uuid}: {type(exc).__name__}: {exc}')
        for i in range(len(light_positions)):
            (OUTPUT_DIR / f'{uuid}_{i}.png').unlink(missing_ok=True)
        return False
    finally:
        # if the model doesn't accept 1 euro payment then kick them out
        # Also clean up objects if a glTF import failed halfway through.
        remove_model(list(set(bpy.data.objects) - before))


def setup_scene():
    # Clear Blender's default cube, camera, and light before controlled rendering.
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if bpy.app.version >= (4, 2, 0) else 'BLENDER_EEVEE'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = 'RGB'
    scene.world.color = (0, 0, 0)
    # Disable ambient illumination so the only changing illumination is our point light.
    # The fixed fill light is intentionally retained for visibility.
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    if background:
        background.inputs['Color'].default_value = (0, 0, 0, 1)
        background.inputs['Strength'].default_value = 0
    # Render all models consistently without a photographic color grade.
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'Medium High Contrast'
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1


def ordered_categories(categories):
    # Avoid obscure, low-information categories found in the first 20 dataset keys.
    lowered = {name.lower(): name for name in categories}
    result = []
    for preferred in PREFERRED_CATEGORIES:
        key = lowered.get(preferred.lower())
        if key is not None and key not in result:
            result.append(key)
    return result


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # download the objects that needs to be modelled through Objaverse
    # do check if we already have them
    models_already_downloaded()
    # once the models are downloaded in the /data/models count should be 20
    # we need to setup the camera and lighting for photo session -> say "cheese"
    setup_scene()
    camera = setup_camera()
    light = setup_light()
    material = setup_neutral_material()

    # let's call in the models
    print(f'PIPELINE_VERSION: {PIPELINE_VERSION}')
    categories = objaverse.load_lvis_annotations()
    print('CURATED_CATEGORIES:', ordered_categories(categories)[:TARGET_MODELS])
    accepted = []
    attempted = set()
    # Prefer the first 20 object categories; expand if a category has no suitable models.
    # Here the preference list replaces arbitrary alphabetical selection.
    for category in ordered_categories(categories):
        if len(accepted) == TARGET_MODELS:
            break
        uids = categories[category]
        existing = [uid for uid in uids if (MODEL_DIR / f'{uid}.glb').is_file()]
        new_candidates = [uid for uid in uids if uid not in existing][:MAX_CANDIDATES_PER_CATEGORY]
        candidates = list(dict.fromkeys(existing + new_candidates))
        # Batched metadata is more efficient than one request per UID.
        try:
            annotations = objaverse.load_annotations(candidates) if candidates else {}
        except Exception as exc:
            print(f'{category}: annotation fetch failed: {exc}')
            annotations = {}
        # Existing files first; other candidates must pass the metadata filters.
        # Revalidate cached files too: otherwise stale, wrongly labelled models sneak in.
        choices = [uid for uid in candidates
                   if model_metadata_ok(annotations.get(uid, {}))
                   and model_label_ok(category, annotations.get(uid, {}))]
        for uuid in choices:
            if uuid in attempted:
                continue
            attempted.add(uuid)
            path = MODEL_DIR / f'{uuid}.glb'
            if not path.is_file():
                try:
                    models = objaverse.load_objects(uids=[uuid])
                    source_path = models.get(uuid)
                    if not source_path or not Path(source_path).is_file():
                        print(f'SKIP {uuid}: download missing')
                        continue
                    path = Path(source_path)
                    if path.suffix.lower() != '.glb':
                        print(f'SKIP {uuid}: unsupported format {path.suffix}')
                        continue
                except Exception as exc:
                    print(f'SKIP {uuid}: download failed: {exc}')
                    continue
            if try_candidate(uuid, path, camera, light, material):
                destination = MODEL_DIR / f'{uuid}.glb'
                if path != destination:
                    shutil.copy2(path, destination)
                accepted.append({'category': category, 'uid': uuid})
                print(f'ACCEPT {category}: {uuid} ({len(accepted)}/{TARGET_MODELS})')
                break
        if not any(item['category'] == category for item in accepted):
            print(f'{category}: no suitable model; moving to next category')

    (OUTPUT_DIR / 'accepted_models.json').write_text(
        json.dumps({'pipeline_version': PIPELINE_VERSION, 'models': accepted}, indent=2),
        encoding='utf-8'
    )
    image_files = list(OUTPUT_DIR.glob('*.png'))
    print(f'Rendered {len(accepted)} models, {len(accepted) * 5} images')
    if len(image_files) != len(accepted) * 5:
        print(f'WARNING: output has {len(image_files)} PNGs; old renders may remain. Run clean_generated.sh renders before rerunning.')
    if len(accepted) != TARGET_MODELS:
        print('WARNING: fewer than 20 models passed. Review category availability / thresholds.')


if __name__ == '__main__':
    main()
