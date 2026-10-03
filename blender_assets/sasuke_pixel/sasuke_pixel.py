"""Pixel-art (voxel) chibi Sasuke for Blender.

Usage inside Blender:  Scripting tab -> Open this file -> Run Script.
Usage headless:        blender -b -P sasuke_pixel.py -- --out sasuke.blend --render preview.png [--cpu]
                       (or `python sasuke_pixel.py ...` with the `bpy` pip module)

Each sprite pixel becomes a cube; only outward faces are generated so the
result is a single clean mesh with one material per palette colour.
"""

import sys

# Sprite, top row first. "." is empty.
PIXELS = [
    "......K.....K.......",
    ".....KHK...KHK..K...",
    "..K.KHHHK.KHHHKKHK..",
    ".KHKHHHHHKHHHHHHHHK.",
    ".KHHHHhHHHHHHhHHHHHK",
    "..KHHHHHHHHHHHHHHHK.",
    "..KBBBMMMMMMMMBBBBK.",
    "..KBBMMmMmmMmMMBBBKK",
    "..KHBBBBBBBBBBBBBHKB",
    "..KHHSHHSSSHHSSHHHK.",
    "..KHSSSSSSSSSSSSSHK.",
    "..KHSEESSSSSSEESSHK.",
    "..KHSEESSSSSSEESSHK.",
    "..KHSSSSSSSSSSSSSHK.",
    "...KHSSSSssSSSSSHK..",
    "....KHSSSSSSSSSHK...",
    "....KNNSSSSSSNNK....",
    "...KNNNNSSSSNNNNK...",
    "..KNNNNNNNNNNNNNNK..",
    ".KNNNNNNNNNNNNNNNNK.",
    ".KWWNNNNNNNNNNNNWWK.",
    ".KWWKNNNNNNNNNNKWWK.",
    ".KWWKNNnNNNNnNNKWWK.",
    ".KSSKNNNNNNNNNNKSSK.",
    "..KKKWWWWWWWWWWKKK..",
    "....KWWWWWWWWWWK....",
    "....KWWWwKKwWWWK....",
    "....KWWWK..KWWWK....",
    "....KSwSK..KSSSK....",
    "....KSwSK..KSSSK....",
    "....KNNNK..KNNNK....",
    "....KKKKK..KKKKK....",
]

PALETTE = {
    "K": ("Outline",       (0.10, 0.10, 0.14)),
    "H": ("Hair",          (0.13, 0.14, 0.23)),
    "h": ("HairHighlight", (0.23, 0.25, 0.39)),
    "B": ("HeadbandCloth", (0.17, 0.24, 0.48)),
    "M": ("HeadbandMetal", (0.72, 0.76, 0.80)),
    "m": ("HeadbandLeaf",  (0.45, 0.50, 0.56)),
    "S": ("Skin",          (0.96, 0.82, 0.69)),
    "s": ("SkinShadow",    (0.85, 0.66, 0.53)),
    "E": ("Eyes",          (0.08, 0.08, 0.10)),
    "N": ("Shirt",         (0.17, 0.23, 0.40)),
    "n": ("ShirtShadow",   (0.12, 0.16, 0.30)),
    "W": ("White",         (0.93, 0.93, 0.93)),
    "w": ("WhiteShadow",   (0.74, 0.74, 0.79)),
}

VOXEL = 0.1   # metres per pixel (sprite is ~3.2 m tall at 0.1)
DEPTH = 2     # voxel layers front-to-back

for i, row in enumerate(PIXELS):
    assert len(row) == len(PIXELS[0]), f"row {i} has width {len(row)}"
    for ch in row:
        assert ch == "." or ch in PALETTE, f"row {i}: unknown colour {ch!r}"


def filled(x, y):
    return 0 <= y < len(PIXELS) and 0 <= x < len(PIXELS[0]) and PIXELS[y][x] != "."


def build_mesh(bpy):
    import bmesh

    keys = sorted({c for row in PIXELS for c in row if c != "."})
    mesh = bpy.data.meshes.new("Sasuke")
    obj = bpy.data.objects.new("Sasuke", mesh)
    bpy.context.collection.objects.link(obj)

    for key in keys:
        name, rgb = PALETTE[key]
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.diffuse_color = (*rgb, 1.0)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
            bsdf.inputs["Roughness"].default_value = 1.0
        mesh.materials.append(mat)
    mat_index = {k: i for i, k in enumerate(keys)}

    bm = bmesh.new()
    verts = {}

    def v(x, y, z):
        if (x, y, z) not in verts:
            verts[(x, y, z)] = bm.verts.new((x * VOXEL, y * VOXEL, z * VOXEL))
        return verts[(x, y, z)]

    w, h = len(PIXELS[0]), len(PIXELS)
    for py, row in enumerate(PIXELS):
        for px, ch in enumerate(row):
            if ch == ".":
                continue
            # Blender coords: X right, Z up, Y depth (front faces -Y).
            x0, z0 = px - w // 2, h - 1 - py
            quads = [((x0, 0, z0), (x0 + 1, 0, z0), (x0 + 1, 0, z0 + 1), (x0, 0, z0 + 1)),  # front
                     ((x0, DEPTH, z0), (x0, DEPTH, z0 + 1), (x0 + 1, DEPTH, z0 + 1), (x0 + 1, DEPTH, z0))]  # back
            if not filled(px - 1, py):
                quads.append(((x0, 0, z0), (x0, 0, z0 + 1), (x0, DEPTH, z0 + 1), (x0, DEPTH, z0)))
            if not filled(px + 1, py):
                quads.append(((x0 + 1, 0, z0), (x0 + 1, DEPTH, z0), (x0 + 1, DEPTH, z0 + 1), (x0 + 1, 0, z0 + 1)))
            if not filled(px, py - 1):  # above
                quads.append(((x0, 0, z0 + 1), (x0 + 1, 0, z0 + 1), (x0 + 1, DEPTH, z0 + 1), (x0, DEPTH, z0 + 1)))
            if not filled(px, py + 1):  # below
                quads.append(((x0, 0, z0), (x0, DEPTH, z0), (x0 + 1, DEPTH, z0), (x0 + 1, 0, z0)))
            for q in quads:
                face = bm.faces.new([v(*p) for p in q])
                face.material_index = mat_index[ch]

    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False
    return obj


def setup_scene(bpy, obj):
    import math

    scene = bpy.context.scene
    w, h = len(PIXELS[0]), len(PIXELS)

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = h * VOXEL * 1.15
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0, -10, h * VOXEL / 2)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = cam

    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = 3.0
    sun = bpy.data.objects.new("Sun", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(-30))

    # Flat, exact-colour look: Workbench with material colours and no shading.
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "FLAT"
    scene.display.shading.color_type = "MATERIAL"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = True
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.filter_size = 0.0  # crisp pixel edges


def main(argv):
    import bpy

    out_blend = out_png = None
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
        if "--out" in args:
            out_blend = args[args.index("--out") + 1]
        if "--render" in args:
            out_png = args[args.index("--render") + 1]

    for name in ("Sasuke", "Camera", "Sun", "Cube", "Light"):
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    obj = build_mesh(bpy)
    setup_scene(bpy, obj)

    if out_blend:
        bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    if out_png:
        if "--cpu" in argv:  # for machines without a GPU/OpenGL context
            scene = bpy.context.scene
            scene.render.engine = "CYCLES"
            scene.cycles.device = "CPU"
            scene.cycles.samples = 16
            scene.world = scene.world or bpy.data.worlds.new("World")
            scene.world.color = (1, 1, 1)
        bpy.context.scene.render.filepath = out_png
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main(sys.argv)
