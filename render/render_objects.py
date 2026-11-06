"""
render_objects.py — render 3D meshes under hard, directional light (Project Part 1, Task 1).

WHY HARD LIGHT? A Mooney image is only interesting if light and shadow cut the
object into big black/white regions. Soft or frontal light gives you a plain
silhouette. So every render here uses ONE sharp sun light from the side/top,
zero ambient light and a black background, as in the paper.

DESIGN (default): N objects x 5 light directions. With 20 objects you get 100
images. Pose and camera stay fixed per object; only the light moves. That lets
you later ask "which light direction breaks the vision models?" (Part 3).

OUTPUTS
    <out>/obj07_teapot_L2.png      RGBA render (transparent background)
    <gt>/depth/obj07_teapot_L2.npy  ground-truth depth (float32, 0 = background)
    <gt>/depth/obj07_teapot_L2.png  depth visualised (for slides)
    <gt>/normal/...npy / .png       ground-truth camera-space surface normals
    <out>/../metadata.csv           object, category, light azimuth/elevation, ...

RUN (either way works)
    # A) with Blender installed (Windows example):
    "C:\\Program Files\\Blender Foundation\\Blender 4.5\\blender.exe" -b -P render_objects.py -- --meshes meshes --out ../Original
    # B) with the pip module:  pip install bpy   (needs a matching Python version)
    python render_objects.py --meshes meshes --out ../Original

Useful flags: --samples 64  --res 512  --no-gt  --limit 2 (quick test on 2 objects)
              --lights 1 (one image per object, for previewing candidate meshes)
"""

import argparse
import csv
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

# 5 light directions (azimuth, elevation) in degrees, relative to the camera.
# Azimuth 0 = light comes from the camera; +90 = from the right; -90 = left.
# All are far from frontal on purpose -> strong shadows -> good Mooneys.
LIGHTS = [(-90, 20), (90, 20), (-45, 60), (45, 45), (0, 80)]

CAM_DISTANCE = 2.6     # camera distance from the object centre
CAM_ELEVATION = 15     # camera looks slightly down at the object (degrees)
OBJECT_RADIUS = 0.85   # every object is scaled to fit a sphere of this radius


# --------------------------------------------------------------------------
# Scene setup
# --------------------------------------------------------------------------
def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("--meshes", required=True, help="folder with .glb/.gltf/.obj/.ply files")
    p.add_argument("--out", default="../Original", help="output folder for RGB renders")
    p.add_argument("--gt", default="../GT", help="output folder for ground-truth depth/normals")
    p.add_argument("--res", type=int, default=512)
    p.add_argument("--samples", type=int, default=64, help="Cycles samples (more = less noise, slower)")
    p.add_argument("--light-strength", type=float, default=4.0)
    p.add_argument("--no-gt", action="store_true", help="skip ground-truth depth/normals")
    p.add_argument("--limit", type=int, default=0, help="only render the first N objects (testing)")
    p.add_argument("--lights", type=int, default=len(LIGHTS),
                   help="use only the first N light directions (e.g. 1 for a quick preview)")
    return p.parse_args(argv)


def setup_render(scene, res, samples):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True          # background alpha = 0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    try:
        scene.view_settings.view_transform = "Standard"   # no filmic "washed out" look
    except TypeError:
        pass
    # Black world, zero strength -> no ambient light at all.
    world = bpy.data.worlds.new("BlackWorld")
    scene.world = world
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0, 0, 0, 1)
        bg.inputs["Strength"].default_value = 0.0
    use_gpu_if_available(scene)


def use_gpu_if_available(scene):
    """Try OptiX, then CUDA (NVIDIA), then others; otherwise stay on CPU."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        print("Cycles preferences not found -> rendering on CPU")
        return
    for backend in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
        except TypeError:
            continue
        gpus = [d for d in prefs.devices if d.type == backend]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == backend
            scene.cycles.device = "GPU"
            print(f"Rendering on GPU via {backend}: {[d.name for d in gpus]}")
            return
    print("No GPU found -> rendering on CPU (slower, but works)")


def clear_objects():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.orphans_purge(do_recursive=True)


def import_mesh(path):
    before = set(bpy.data.objects)
    ext = path.suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=str(path))
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=str(path))
    else:
        raise ValueError(f"Unsupported mesh format: {path}")
    return [o for o in bpy.data.objects if o not in before]


def normalize(objects):
    """Centre the object at the origin and scale it to OBJECT_RADIUS."""
    bpy.context.view_layer.update()
    meshes = [o for o in objects if o.type == "MESH"]
    if not meshes:
        raise ValueError("file contains no mesh")
    corners = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    lo = Vector([min(c[i] for c in corners) for i in range(3)])
    hi = Vector([max(c[i] for c in corners) for i in range(3)])
    centre, radius = (lo + hi) / 2, (hi - lo).length / 2
    s = OBJECT_RADIUS / max(radius, 1e-9)
    T = Matrix.Scale(s, 4) @ Matrix.Translation(-centre)
    for o in objects:
        if o.parent is None:              # transform only the roots
            o.matrix_world = T @ o.matrix_world
    bpy.context.view_layer.update()


def direction(az_deg, el_deg):
    """Unit vector for azimuth/elevation; azimuth 0 points towards the camera (-Y)."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))


def add_camera(scene):
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(cam)
    cam.data.lens = 50
    cam.location = direction(0, CAM_ELEVATION) * CAM_DISTANCE
    cam.rotation_euler = (-cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    return cam


def add_sun(scene, strength):
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", type="SUN"))
    scene.collection.objects.link(sun)
    sun.data.energy = strength
    sun.data.angle = math.radians(0.5)    # tiny angle -> hard shadow edges
    return sun


def aim_sun(sun, az, el):
    # A sun light shines along its local -Z axis; point -Z from the light to the object.
    sun.rotation_euler = (-direction(az, el)).to_track_quat("-Z", "Y").to_euler()


# --------------------------------------------------------------------------
# Ground truth by ray casting (exact, no colour-management surprises)
# --------------------------------------------------------------------------
def ground_truth(scene, cam, res):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    frame = [cam.matrix_world @ v for v in cam.data.view_frame(scene=scene)]
    # view_frame order: top-right, bottom-right, bottom-left, top-left
    tr, br, bl, tl = frame
    origin = cam.matrix_world.translation
    forward = (cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
    cam_rot_inv = cam.matrix_world.to_3x3().inverted()
    depth = np.zeros((res, res), np.float32)
    normal = np.zeros((res, res, 3), np.float32)
    for y in range(res):
        fy = (y + 0.5) / res
        left, right = tl.lerp(bl, fy), tr.lerp(br, fy)
        for x in range(res):
            target = left.lerp(right, (x + 0.5) / res)
            hit, loc, n, *_ = scene.ray_cast(depsgraph, origin, (target - origin).normalized())
            if hit:
                depth[y, x] = (loc - origin).dot(forward)
                nc = cam_rot_inv @ n
                if nc.z < 0:              # make normals face the camera
                    nc = -nc
                normal[y, x] = nc[:]
    return depth, normal


def save_gt_images(depth, normal, stem, gt_dir):
    import struct, zlib  # tiny PNG writer so we don't need extra packages inside Blender

    def write_png(path, arr):
        h, w = arr.shape[:2]
        ch = 1 if arr.ndim == 2 else arr.shape[2]
        raw = b"".join(b"\x00" + arr[r].tobytes() for r in range(h))
        def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
        ctype = {1: 0, 3: 2}[ch]
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))

    (gt_dir / "depth").mkdir(parents=True, exist_ok=True)
    (gt_dir / "normal").mkdir(parents=True, exist_ok=True)
    np.save(gt_dir / "depth" / f"{stem}.npy", depth)
    np.save(gt_dir / "normal" / f"{stem}.npy", normal)
    fg = depth > 0
    vis = np.zeros_like(depth)
    if fg.any():                          # near = bright, far = dark
        d0, d1 = depth[fg].min(), depth[fg].max()
        vis[fg] = 1.0 - (depth[fg] - d0) / max(d1 - d0, 1e-6) * 0.8
    write_png(gt_dir / "depth" / f"{stem}.png", (vis * 255).astype(np.uint8))
    nvis = np.where(fg[..., None], (normal * 0.5 + 0.5) * 255, 0).astype(np.uint8)
    write_png(gt_dir / "normal" / f"{stem}.png", np.ascontiguousarray(nvis))


# --------------------------------------------------------------------------
def main():
    a = parse_args()
    exts = {".glb", ".gltf", ".obj", ".ply", ".stl"}
    meshes = sorted(p for p in Path(a.meshes).iterdir() if p.suffix.lower() in exts)
    if a.limit:
        meshes = meshes[:a.limit]
    if not meshes:
        sys.exit(f"No meshes found in {a.meshes}")
    out, gt = Path(a.out).resolve(), Path(a.gt).resolve()
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    setup_render(scene, a.res, a.samples)

    rows, t0 = [], time.time()
    for i, mesh in enumerate(meshes):
        category = mesh.stem.split("__")[0]       # file "teapot__uid.glb" -> "teapot"
        clear_objects()
        try:
            normalize(import_mesh(mesh))
        except Exception as e:
            print(f"!! skipping {mesh.name}: {e}")
            continue
        cam, sun = add_camera(scene), add_sun(scene, a.light_strength)
        depth = normal = None
        if not a.no_gt:                           # same geometry for all 5 lights
            depth, normal = ground_truth(scene, cam, a.res)
        for k, (az, el) in enumerate(LIGHTS[:a.lights]):
            stem = f"obj{i:02d}_{category}_L{k}"
            aim_sun(sun, az, el)
            scene.render.filepath = str(out / f"{stem}.png")
            bpy.ops.render.render(write_still=True)
            if depth is not None:
                save_gt_images(depth, normal, stem, gt)
            rows.append([f"{stem}.png", i, category, mesh.name, k, az, el])
            print(f"[{len(rows):>3}] {stem}.png  light az={az} el={el}  ({time.time() - t0:.0f}s)")

    with open(out.parent / "metadata.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "object_id", "category", "mesh_file", "light_id", "light_azimuth", "light_elevation"])
        w.writerows(rows)
    print(f"Done: {len(rows)} renders in {out}  (metadata: {out.parent / 'metadata.csv'})")


if __name__ == "__main__":
    main()
