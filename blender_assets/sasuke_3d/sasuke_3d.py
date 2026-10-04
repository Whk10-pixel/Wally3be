"""Stylized 3D game-style Sasuke (classic outfit) for Blender 4.2+ / 5.x.

Usage inside Blender:  Scripting tab -> Open this file -> Run Script.
Usage headless:        blender -b -P sasuke_3d.py -- --out sasuke_3d.blend --render preview.png [--cpu]
                       (or `python sasuke_3d.py ...` with the `bpy` pip module)

Everything is procedural: the body is built from lathed profiles, the hair
from curved tapered clumps, and a cel-style ink outline comes from an
inverted-hull Solidify modifier (works in EEVEE and Cycles). All parts live
in the "Sasuke" collection; arms hang off empties so they can be posed.
"""

import math
import sys

import bpy  # must precede bmesh when using the pip `bpy` module
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HZ = 1.32        # head centre height (character is ~1.8 m tall incl. hair)
OUTLINE = 0.008  # ink line thickness

COL = None
MATS = {}


# --------------------------------------------------------------------------- materials

def principled(name, rgb, rough=0.6, metal=0.0, spec=0.3, coat=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1.0)
    if not m.node_tree:
        m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    for key, val in (("Base Color", (*rgb, 1.0)), ("Roughness", rough), ("Metallic", metal),
                     ("Specular IOR Level", spec), ("Coat Weight", coat)):
        if key in b.inputs:
            b.inputs[key].default_value = val
    return m


def outline_material():
    m = bpy.data.materials.get("Ink") or bpy.data.materials.new("Ink")
    m.diffuse_color = (0.02, 0.02, 0.035, 1.0)
    if not m.node_tree:
        m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    ink = nt.nodes.new("ShaderNodeEmission")
    ink.inputs["Color"].default_value = (0.02, 0.02, 0.035, 1.0)
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    # The hull's normals point inward: its near side is back-facing (made
    # invisible) and only the far side peeks out around the silhouette.
    # Shadow and bounce rays always pass through, so the hull casts no shade.
    path = nt.nodes.new("ShaderNodeLightPath")
    front = nt.nodes.new("ShaderNodeMath")
    front.operation = "SUBTRACT"
    front.inputs[0].default_value = 1.0
    nt.links.new(geo.outputs["Backfacing"], front.inputs[1])
    show = nt.nodes.new("ShaderNodeMath")
    show.operation = "MULTIPLY"
    nt.links.new(path.outputs["Is Camera Ray"], show.inputs[0])
    nt.links.new(front.outputs["Value"], show.inputs[1])
    hide = nt.nodes.new("ShaderNodeMath")
    hide.operation = "SUBTRACT"
    hide.inputs[0].default_value = 1.0
    nt.links.new(show.outputs["Value"], hide.inputs[1])
    nt.links.new(hide.outputs["Value"], mix.inputs["Fac"])
    nt.links.new(ink.outputs["Emission"], mix.inputs[1])
    nt.links.new(clear.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    m.use_backface_culling = True
    if hasattr(m, "surface_render_method"):
        m.surface_render_method = "DITHERED"
    if hasattr(m, "use_transparent_shadow"):
        m.use_transparent_shadow = True
    return m


def build_materials():
    MATS.update(
        skin=principled("Skin", (0.93, 0.70, 0.56), rough=0.55, spec=0.2),
        skin_dark=principled("SkinShade", (0.82, 0.56, 0.45), rough=0.6, spec=0.1),
        hair=principled("Hair", (0.035, 0.04, 0.075), rough=0.32, spec=0.6),
        shirt=principled("Shirt", (0.035, 0.055, 0.16), rough=0.75, spec=0.15),
        white=principled("Cloth White", (0.80, 0.80, 0.78), rough=0.8, spec=0.15),
        band=principled("Headband Cloth", (0.03, 0.05, 0.17), rough=0.8, spec=0.1),
        metal=principled("Headband Metal", (0.75, 0.78, 0.82), rough=0.25, metal=1.0),
        engrave=principled("Engraving", (0.12, 0.13, 0.15), rough=0.4, metal=1.0),
        eye_white=principled("Eye White", (0.97, 0.97, 0.98), rough=0.3),
        iris=principled("Iris", (0.04, 0.035, 0.05), rough=0.15, spec=0.8, coat=1.0),
        lash=principled("Lash", (0.02, 0.02, 0.03), rough=0.6),
        highlight=principled("Eye Shine", (1.0, 1.0, 1.0), rough=0.2),
        mouth=principled("Mouth", (0.45, 0.20, 0.20), rough=0.6),
        crest_red=principled("Crest Red", (0.70, 0.04, 0.04), rough=0.6),
        sandal=principled("Sandal", (0.06, 0.08, 0.18), rough=0.6),
        strap=principled("Strap", (0.12, 0.10, 0.10), rough=0.7),
        stage=principled("Stage", (0.20, 0.22, 0.30), rough=0.5),
        stage_rim=principled("Stage Rim", (0.70, 0.05, 0.06), rough=0.4),
        ink=outline_material(),
    )


# --------------------------------------------------------------------------- mesh helpers

def add_obj(name, bm, mat, smooth=True, subsurf=0, outline=OUTLINE, parent=None, loc=(0, 0, 0)):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    me.materials.append(MATS[mat])
    for p in me.polygons:
        p.use_smooth = smooth
    if subsurf:
        mod = ob.modifiers.new("Subdivision", "SUBSURF")
        mod.levels = mod.render_levels = subsurf
    if outline:
        me.materials.append(MATS["ink"])
        mod = ob.modifiers.new("Ink Outline", "SOLIDIFY")
        mod.thickness = outline
        mod.offset = 1.0
        mod.use_flip_normals = True
        mod.use_rim = False
        mod.material_offset = 1
    ob.parent = parent
    ob.location = loc
    return ob


def lathe(profile, segs=32, arc=None):
    """Revolve rings (z, rx, ry[, yoff]) around Z. a=0 is the front (-Y).

    arc=(a0, a1) makes an open sheet instead of a closed solid.
    """
    bm = bmesh.new()
    rings = []
    n = segs if arc is None else segs + 1
    a0, a1 = arc if arc else (0.0, 2 * math.pi)
    for ring in profile:
        z, rx, ry = ring[:3]
        yoff = ring[3] if len(ring) > 3 else 0.0
        if rx == 0 and ry == 0:
            rings.append([bm.verts.new((0, yoff, z))])
            continue
        pts = []
        for i in range(n):
            a = a0 + (a1 - a0) * i / segs
            pts.append(bm.verts.new((rx * math.sin(a), yoff - ry * math.cos(a), z)))
        rings.append(pts)
    for r0, r1 in zip(rings, rings[1:]):
        if len(r0) == 1 or len(r1) == 1:
            ring, tip = (r1, r0[0]) if len(r0) == 1 else (r0, r1[0])
            for i in range(len(ring) - (0 if arc is None else 1)):
                bm.faces.new((ring[i], ring[(i + 1) % len(ring)], tip))
            continue
        for i in range(n - (0 if arc is None else 1)):
            j = (i + 1) % n
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    if arc is None:
        for ring in (rings[0], rings[-1]):
            if len(ring) > 2:
                bm.faces.new(ring)
    return bm


def sphere(radius=1.0, scale=(1, 1, 1), segs=24, rings=14):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=radius)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    return bm


def rounded_box(size, bevel=0.3):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(size) * bevel, segments=3,
                    profile=0.5, affect="EDGES")
    return bm


def add_clump(bm, p0, p1, p2, r0, flat=0.55, centre=None, steps=12, segs=10, taper=1.0):
    """Curved, tapered, flattened strand along a quadratic Bezier (hair / ribbons)."""
    centre = centre or Vector((0, 0, HZ))
    prev = None
    for s in range(steps + 1):
        t = s / steps
        p = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2
        tan = (2 * (1 - t) * (p1 - p0) + 2 * t * (p2 - p1)).normalized()
        if s == steps:
            tip = bm.verts.new(p)
            for i in range(segs):
                bm.faces.new((prev[i], prev[(i + 1) % segs], tip))
            break
        radial = p - centre
        nrm = (radial - tan * radial.dot(tan)).normalized()
        bi = tan.cross(nrm)
        r = r0 * (1 - t) ** taper
        ring = [bm.verts.new(p + bi * r * math.cos(2 * math.pi * i / segs)
                             + nrm * r * flat * math.sin(2 * math.pi * i / segs))
                for i in range(segs)]
        if prev is None:
            bm.faces.new(list(reversed(ring)))
        else:
            for i in range(segs):
                j = (i + 1) % segs
                bm.faces.new((prev[i], prev[j], ring[j], ring[i]))
        prev = ring


class Surface:
    """Ray-casts against already-built (evaluated) objects to stick parts onto them."""

    def __init__(self, *objs):
        inks = [m for o in objs for m in o.modifiers if m.name == "Ink Outline"]
        for m in inks:  # cast against the real surface, not the outline hull
            m.show_viewport = False
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        self.trees = [BVHTree.FromObject(o, dg) for o in objs]
        for m in inks:
            m.show_viewport = True
        self.mats = [o.matrix_world.copy() for o in objs]

    def hit(self, origin, direction):
        best = None
        for tree, mw in zip(self.trees, self.mats):
            inv = mw.inverted()
            loc, nrm, _, dist = tree.ray_cast(inv @ origin, (inv.to_3x3() @ direction).normalized())
            if loc is not None and (best is None or dist < best[2]):
                best = (mw @ loc, (mw.to_3x3() @ nrm).normalized(), dist)
        return best

    def front(self, x, z):
        """Point + normal on the surface seen from the front (-Y) at (x, z)."""
        loc, nrm, _ = self.hit(Vector((x, -3, z)), Vector((0, 1, 0)))
        return loc, nrm

    def radial(self, direction, centre):
        """Outermost surface point along a direction from a centre."""
        d = Vector(direction).normalized()
        loc, nrm, _ = self.hit(centre + d * 3, -d)
        return loc, nrm


def place_on(name, bm, mat, loc, nrm, push=0.0, spin=0.0, outline=0.0, subsurf=0):
    """Add an object whose local Z follows a surface normal (local Y ~ up)."""
    ob = add_obj(name, bm, mat, outline=outline, subsurf=subsurf)
    q = nrm.to_track_quat("Z", "Y")
    ob.matrix_world = (Matrix.Translation(loc + nrm * push) @ q.to_matrix().to_4x4()
                       @ Matrix.Rotation(spin, 4, "Z"))
    return ob


# --------------------------------------------------------------------------- body parts

def build_head():
    c = HZ
    head = add_obj("Head", lathe([
        (c - 0.30, 0.0, 0.0, -0.05),
        (c - 0.295, 0.05, 0.04, -0.05),
        (c - 0.26, 0.12, 0.11, -0.035),
        (c - 0.19, 0.20, 0.19, -0.015),
        (c - 0.10, 0.26, 0.245, 0.0),
        (c + 0.00, 0.29, 0.27, 0.0),
        (c + 0.10, 0.30, 0.285, 0.01),
        (c + 0.19, 0.28, 0.275, 0.015),
        (c + 0.26, 0.22, 0.22, 0.015),
        (c + 0.31, 0.12, 0.12, 0.015),
        (c + 0.325, 0.0, 0.0, 0.015),
    ], segs=40), "skin", subsurf=2)

    for side in (-1, 1):
        ear = add_obj(f"Ear.{'L' if side > 0 else 'R'}", sphere(0.06, (0.55, 0.9, 1.1)), "skin",
                      subsurf=1, loc=(side * 0.285, 0.03, c - 0.04))
        ear.rotation_euler = (0, side * 0.2, 0)
    add_obj("Neck", lathe([(0.95, 0.075, 0.07), (c - 0.18, 0.07, 0.065, 0.01)], segs=20),
            "skin", subsurf=1)
    return head


def build_face(head):
    surf = Surface(head)
    c = HZ
    for side in (-1, 1):
        tag = "L" if side > 0 else "R"
        x, z = side * 0.115, c - 0.045
        loc, nrm = surf.front(x, z)
        tilt = side * -0.10
        place_on(f"Eye White.{tag}", sphere(1, (0.066, 0.05, 0.012)), "eye_white", loc, nrm,
                 push=-0.002, spin=tilt)
        place_on(f"Iris.{tag}", sphere(1, (0.034, 0.044, 0.008)), "iris",
                 loc + Vector((-side * 0.01, 0, -0.002)), nrm, push=0.008)
        place_on(f"Eye Shine.{tag}", sphere(1, (0.013, 0.015, 0.006)), "highlight",
                 loc + Vector((side * 0.0, 0, 0.016)), nrm, push=0.016)
        place_on(f"Eye Shine Small.{tag}", sphere(1, (0.006, 0.006, 0.004)), "highlight",
                 loc + Vector((-side * 0.022, 0, -0.018)), nrm, push=0.015)
        # Sharp upper lash line, flicked up at the outer corner.
        lash = bmesh.new()
        add_clump(lash, Vector((-0.085, -0.004, 0)), Vector((0.0, 0.03, 0)), Vector((0.092, 0.016, 0)),
                  0.013, flat=0.5, centre=Vector((0, 0, -1)), taper=0.35)
        if side < 0:
            bmesh.ops.scale(lash, vec=(-1, 1, 1), verts=lash.verts)
        lloc, lnrm = surf.front(x, z + 0.04)
        place_on(f"Lash.{tag}", lash, "lash", lloc, lnrm, push=0.006, spin=0)
        # Low, angled brows give him the trademark scowl.
        brow = bmesh.new()
        add_clump(brow, Vector((-side * 0.07, -0.014, 0)), Vector((0, 0.002, 0)),
                  Vector((side * 0.07, 0.016, 0)), 0.011, flat=0.5, centre=Vector((0, 0, -1)), taper=0.7)
        bloc, bnrm = surf.front(side * 0.12, z + 0.088)
        place_on(f"Brow.{tag}", brow, "lash", bloc, bnrm, push=0.003)
        # Faint blush/shade on the cheek bones is too cute for Sasuke; skip.

    nloc, nnrm = surf.front(0.0, c - 0.135)
    place_on("Nose", sphere(1, (0.012, 0.010, 0.008)), "skin_dark", nloc, nnrm, push=-0.002)
    mouth = bmesh.new()
    add_clump(mouth, Vector((-0.028, -0.003, 0)), Vector((0, 0.004, 0)), Vector((0.028, -0.003, 0)),
              0.0055, flat=0.5, centre=Vector((0, 0, -1)), taper=0.3)
    mloc, mnrm = surf.front(0.0, c - 0.205)
    place_on("Mouth", mouth, "mouth", mloc, mnrm, push=0.001)


def build_hair(head):
    c = HZ
    centre = Vector((0, 0.02, c + 0.02))

    # Skull cap: an inflated copy of the head, trimmed back from the face.
    cap = sphere(1, (0.325, 0.32, 0.345), segs=40, rings=24)
    bmesh.ops.translate(cap, vec=(0, 0.012, c + 0.02), verts=cap.verts)
    doomed = [v for v in cap.verts
              if not (v.co.z > c + 0.13
                      or (v.co.y > -0.06 and v.co.z > c - 0.10)
                      or (v.co.y > 0.10 and v.co.z > c - 0.24))]
    bmesh.ops.delete(cap, geom=doomed, context="VERTS")
    cap_ob = add_obj("Hair Cap", cap, "hair", subsurf=1)
    mod = cap_ob.modifiers.new("Thickness", "SOLIDIFY")
    mod.thickness = 0.02
    cap_ob.modifiers.move(len(cap_ob.modifiers) - 1, 0)

    surf = Surface(head, cap_ob)
    bm = bmesh.new()

    def clump(direction, grow, length, r, bend=(0, 0, 0), flat=0.5, sink=0.06):
        base, nrm = surf.radial(direction, centre)
        p0 = base - nrm * sink
        g = Vector(grow).normalized()
        p2 = base + g * length + Vector(bend)
        p1 = base + g * length * 0.45 + nrm * 0.03
        add_clump(bm, p0, p1, p2, r, flat=flat, centre=centre)

    def sph(az, el):  # az=0 back(+Y), +x to the left side
        return Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))

    # Signature back spikes: three fanned rows sweeping back and up.
    for el, length, r, up in ((0.75, 0.30, 0.10, 0.9), (0.40, 0.38, 0.11, 0.55), (0.05, 0.34, 0.10, 0.25)):
        for az in (-1.05, -0.55, 0.0, 0.55, 1.05):
            d = sph(az, el)
            grow = d + Vector((0, 0.9, up))
            clump(d, grow, length * (1.0 - 0.15 * abs(az)), r, bend=(0, 0, 0.04 * up))
    for az in (-0.8, -0.27, 0.27, 0.8):  # nape tufts
        d = sph(az, -0.35)
        clump(d, d + Vector((0, 0.5, -0.4)), 0.17, 0.08)
    for az in (-0.3, 0.3):  # crown
        d = sph(az, 1.15)
        clump(d, d + Vector((0, 0.8, 0.5)), 0.26, 0.10)

    # Spikes peeking up over the headband at the front.
    for x, lean in ((-0.17, -0.6), (-0.06, -0.2), (0.06, 0.2), (0.17, 0.6)):
        d = Vector((x, -0.7, 0.8))
        clump(d, Vector((lean, 0.2, 1.0)), 0.11, 0.08, flat=0.4)
    # Clumps lying over the crown, swept back, so the cap doesn't read as a helmet.
    for el in (0.95, 1.25):
        for az in (-2.3, -2.6, 2.3, 2.6, 2.95, -2.95):
            d = sph(az, el)
            clump(d, Vector((d.x * 0.6, 1.0, 0.35)), 0.22, 0.09, flat=0.35, sink=0.04)

    # Long bangs framing the face, plus shorter strands by the ears.
    for side in (-1, 1):
        base, nrm = surf.radial(Vector((side * 0.65, -0.55, 0.45)), centre)
        add_clump(bm, base - nrm * 0.05, base + Vector((side * 0.06, -0.08, -0.16)),
                  Vector((side * 0.235, -0.215, c - 0.27)), 0.072, flat=0.45, centre=centre)
        base, nrm = surf.radial(Vector((side * 0.85, -0.35, 0.35)), centre)
        add_clump(bm, base - nrm * 0.05, base + Vector((side * 0.08, -0.06, -0.10)),
                  Vector((side * 0.31, -0.10, c - 0.16)), 0.075, flat=0.45, centre=centre)
        base, nrm = surf.radial(Vector((side * 0.95, -0.05, 0.25)), centre)
        add_clump(bm, base - nrm * 0.05, base + Vector((side * 0.07, 0.0, -0.08)),
                  Vector((side * 0.33, 0.06, c - 0.12)), 0.08, flat=0.45, centre=centre)

    add_obj("Hair Spikes", bm, "hair")
    return cap_ob, surf


def build_headband(surf):
    c = HZ
    centre = Vector((0, 0.0, c + 0.10))
    rings = []
    for dz in (-0.04, 0.04):
        ring = []
        for i in range(48):
            a = 2 * math.pi * i / 48
            d = Vector((math.sin(a), -math.cos(a), 0))
            loc, nrm = surf.radial(d, centre + Vector((0, 0, dz)))
            ring.append(loc + d * 0.008)
        rings.append(ring)
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    for i in range(48):
        j = (i + 1) % 48
        bm.faces.new((vs[0][i], vs[0][j], vs[1][j], vs[1][i]))
    band = add_obj("Headband", bm, "band", subsurf=1)
    mod = band.modifiers.new("Thickness", "SOLIDIFY")
    mod.thickness = -0.012
    band.modifiers.move(len(band.modifiers) - 1, 0)

    # Curved metal plate across the forehead.
    plate_rings = []
    for dz in (-0.048, 0.048):
        ring = []
        for i in range(17):
            a = -0.62 + 1.24 * i / 16
            d = Vector((math.sin(a), -math.cos(a), 0))
            loc, _ = surf.radial(d, centre + Vector((0, 0, dz)))
            ring.append(loc + d * 0.02)
        plate_rings.append(ring)
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in ring] for ring in plate_rings]
    for i in range(16):
        bm.faces.new((vs[0][i], vs[0][i + 1], vs[1][i + 1], vs[1][i]))
    plate = add_obj("Forehead Protector", bm, "metal", smooth=True)
    mod = plate.modifiers.new("Thickness", "SOLIDIFY")
    mod.thickness = -0.012
    bev = plate.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.004
    bev.segments = 2
    plate.modifiers.move(len(plate.modifiers) - 1, 0)
    plate.modifiers.move(len(plate.modifiers) - 1, 0)
    for side in (-1, 1):
        for dz in (-0.03, 0.03):
            a = side * 0.55
            d = Vector((math.sin(a), -math.cos(a), 0))
            loc, _ = surf.radial(d, centre + Vector((0, 0, dz)))
            add_obj("Rivet", sphere(0.007, segs=10, rings=6), "metal", outline=0,
                    loc=loc + d * 0.022)

    # Engraved leaf: a spiral swirl with a pointed tip.
    loc, nrm = surf.radial(Vector((0, -1, 0)), centre)
    face = loc + Vector((0, -1, 0)) * 0.034
    curve = bpy.data.curves.new("Leaf Symbol", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.0035
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    pts = []
    for i in range(46):
        t = i / 45
        ang = 0.6 + t * 2.6 * math.pi
        r = 0.006 + 0.026 * t
        pts.append((r * math.cos(ang), r * math.sin(ang) * 0.95))
    pts += [(pts[-1][0] + 0.03, pts[-1][1] + 0.012), (pts[-1][0] - 0.004, pts[-1][1] + 0.028)]
    spline.points.add(len(pts) - 1)
    for p, (x, z) in zip(spline.points, pts):
        p.co = (x, 0, z - 0.004, 1)
    sym = bpy.data.objects.new("Leaf Symbol", curve)
    COL.objects.link(sym)
    curve.materials.append(MATS["engrave"])
    sym.location = face
    tails(surf, centre)


def tails(surf, centre):
    bm = bmesh.new()
    loc, _ = surf.radial(Vector((0, 1, 0)), centre)
    for side, drop, swing in ((-1, 0.34, 0.07), (1, 0.28, 0.13)):
        p0 = loc + Vector((side * 0.025, 0.0, 0))
        add_clump(bm, p0, p0 + Vector((side * 0.05, 0.09, -0.06)),
                  p0 + Vector((side * swing, 0.11, -drop)), 0.038, flat=0.2,
                  centre=p0 - Vector((0, 0.5, 0)), taper=0.2, segs=8)
    add_obj("Headband Tails", bm, "band")
    knot = add_obj("Headband Knot", sphere(0.035, (1.2, 0.8, 1.0)), "band", subsurf=1,
                   loc=loc + Vector((0, 0.01, 0)))
    return knot


def build_torso():
    shirt = [
        (0.50, 0.215, 0.155), (0.56, 0.212, 0.152), (0.64, 0.205, 0.148), (0.72, 0.195, 0.14),
        (0.84, 0.205, 0.145), (0.92, 0.225, 0.15), (0.97, 0.20, 0.135), (1.0, 0.13, 0.10),
        (1.01, 0.0, 0.0),
    ]
    add_obj("Shirt", lathe(shirt, segs=36), "shirt", subsurf=2)
    # High collar, open at the throat.
    collar = add_obj("Collar", lathe([(0.95, 0.15, 0.125, 0.005), (1.04, 0.135, 0.11, 0.01),
                                      (1.14, 0.165, 0.14, 0.015)], segs=24, arc=(0.55, 2 * math.pi - 0.55)),
                     "shirt", subsurf=2)
    mod = collar.modifiers.new("Thickness", "SOLIDIFY")
    mod.thickness = 0.018
    collar.modifiers.move(len(collar.modifiers) - 1, 0)
    # Shirt hem and shoulder seam shading.
    hem = add_obj("Shirt Hem", lathe([(0.495, 0.218, 0.158), (0.53, 0.218, 0.158)], segs=36),
                  "shirt", subsurf=1, outline=0)
    hem.scale = (1.01, 1.01, 1)
    build_crest(Vector((0, 0.152, 0.84)))


def build_crest(at):
    """Uchiha fan on the back: red top, white bottom, short handle."""
    def half(top):
        bm = bmesh.new()
        n = 20
        centre = bm.verts.new((0, 0, 0))
        rim = []
        for i in range(n + 1):
            a = math.pi * i / n
            rim.append(bm.verts.new((0.075 * math.cos(a), 0, 0.075 * math.sin(a) * (1 if top else -1))))
        for i in range(n):
            bm.faces.new((centre, rim[i], rim[i + 1]))
        bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.006)
        return bm
    for top, mat in ((True, "crest_red"), (False, "white")):
        ob = add_obj("Uchiha Crest " + ("Red" if top else "White"), half(top), mat, smooth=False,
                     outline=0.004, loc=at)
        ob.rotation_euler = (0.12, 0, 0)
    add_obj("Uchiha Crest Handle", rounded_box((0.022, 0.006, 0.07), 0.2), "white", outline=0.004,
            loc=at + Vector((0, 0.012, -0.105)))


def build_arm(side):
    tag = "L" if side > 0 else "R"
    pivot = bpy.data.objects.new(f"Arm.{tag}", None)
    pivot.empty_display_type = "SPHERE"
    pivot.empty_display_size = 0.05
    COL.objects.link(pivot)
    pivot.location = (side * 0.215, 0.0, 0.925)
    pivot.rotation_euler = (-0.05, -side * 0.22, 0)

    add_obj(f"Sleeve.{tag}", lathe([(0.04, 0.0, 0.0), (0.02, 0.07, 0.075), (-0.06, 0.08, 0.08),
                                    (-0.13, 0.078, 0.078), (-0.15, 0.06, 0.06)], segs=20),
            "shirt", subsurf=2, parent=pivot)
    add_obj(f"Upper Arm.{tag}", lathe([(-0.10, 0.052, 0.052), (-0.20, 0.047, 0.047),
                                       (-0.40, 0.042, 0.042)], segs=16), "skin", subsurf=1, parent=pivot)
    add_obj(f"Arm Warmer.{tag}", lathe([(-0.205, 0.0, 0.0), (-0.205, 0.056, 0.056), (-0.24, 0.058, 0.058),
                                        (-0.36, 0.054, 0.054), (-0.385, 0.05, 0.05), (-0.385, 0.0, 0.0)],
                                       segs=20), "white", subsurf=2, parent=pivot)
    add_obj(f"Hand.{tag}", sphere(1, (0.052, 0.042, 0.062)), "skin", subsurf=1, parent=pivot,
            loc=(side * 0.005, 0, -0.445))
    thumb = add_obj(f"Thumb.{tag}", sphere(1, (0.018, 0.018, 0.035)), "skin", subsurf=1, parent=pivot,
                    loc=(-side * 0.03, -0.03, -0.43))
    thumb.rotation_euler = (0.3, side * 0.5, 0)
    return pivot


def build_legs():
    add_obj("Shorts", lathe([(0.58, 0.0, 0.0), (0.58, 0.19, 0.135), (0.50, 0.20, 0.142),
                             (0.44, 0.19, 0.135), (0.40, 0.15, 0.11), (0.39, 0.0, 0.0)], segs=36),
            "white", subsurf=2)
    for side in (-1, 1):
        tag = "L" if side > 0 else "R"
        x = side * 0.092
        add_obj(f"Shorts Leg.{tag}", lathe([(0.46, 0.0, 0.0), (0.46, 0.095, 0.095), (0.34, 0.098, 0.098),
                                            (0.29, 0.1, 0.1), (0.29, 0.0, 0.0)], segs=24),
                "white", subsurf=2, loc=(x, 0, 0))
        add_obj(f"Leg.{tag}", lathe([(0.37, 0.068, 0.068), (0.28, 0.058, 0.058), (0.20, 0.063, 0.068),
                                     (0.12, 0.048, 0.05), (0.05, 0.045, 0.045)], segs=20),
                "skin", subsurf=1, loc=(x, 0, 0))
        # Shin wraps.
        add_obj(f"Leg Wrap.{tag}", lathe([(0.075, 0.0, 0.0), (0.075, 0.052, 0.054), (0.10, 0.054, 0.056),
                                          (0.16, 0.062, 0.066), (0.19, 0.064, 0.068), (0.19, 0.0, 0.0)], segs=20),
                "white", subsurf=2, loc=(x, 0, 0))
        add_obj(f"Sandal.{tag}", rounded_box((0.10, 0.20, 0.035), 0.35), "sandal", subsurf=1,
                loc=(x, -0.035, 0.0175))
        add_obj(f"Foot.{tag}", sphere(1, (0.048, 0.095, 0.04)), "skin", subsurf=1,
                loc=(x, -0.05, 0.05))
        add_obj(f"Sandal Strap.{tag}", lathe([(0.0, 0.054, 0.08), (0.03, 0.054, 0.08)], segs=20),
                "sandal", subsurf=1, loc=(x, -0.02, 0.045))
        add_obj(f"Heel Guard.{tag}", lathe([(0.0, 0.05, 0.05), (0.065, 0.049, 0.049)], segs=20,
                                            arc=(math.pi * 0.55, math.pi * 1.45)),
                "sandal", subsurf=1, loc=(x, 0.0, 0.03))

    # Kunai holster strapped to the right thigh.
    add_obj("Holster", rounded_box((0.05, 0.085, 0.10), 0.25), "band", subsurf=1,
            loc=(-0.18, -0.01, 0.37))
    add_obj("Holster Strap", lathe([(0.0, 0.103, 0.103), (0.022, 0.103, 0.103)], segs=24),
            "band", subsurf=1, outline=0.005, loc=(-0.092, 0, 0.36))
    add_obj("Holster Flap", rounded_box((0.054, 0.09, 0.03), 0.3), "strap", subsurf=1, outline=0.004,
            loc=(-0.18, -0.01, 0.425))


# --------------------------------------------------------------------------- scene

def set_engine(scene, *names):
    for n in names:
        try:
            scene.render.engine = n
            return
        except TypeError:
            continue


def setup_stage(stage_col):
    def link(ob):
        stage_col.objects.link(ob)
        return ob

    scene = bpy.context.scene
    base = lathe([(-0.06, 0.0, 0.0), (-0.06, 0.62, 0.62), (0.0, 0.6, 0.6), (0.0, 0.0, 0.0)], segs=64)
    me = bpy.data.meshes.new("Stage")
    base.to_mesh(me)
    base.free()
    stage = link(bpy.data.objects.new("Stage", me))
    me.materials.append(MATS["stage"])
    rim = lathe([(-0.045, 0.635, 0.635), (-0.03, 0.635, 0.635)], segs=64)
    me = bpy.data.meshes.new("Stage Rim")
    rim.to_mesh(me)
    rim.free()
    link(bpy.data.objects.new("Stage Rim", me)).data.materials.append(MATS["stage_rim"])
    for p in stage.data.polygons:
        p.use_smooth = True

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 70
    cam = link(bpy.data.objects.new("Camera", cam_data))
    target = Vector((0, 0, 0.9))
    cam.location = Vector((1.9, -5.0, 1.55))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    def area(name, loc, energy, color, size):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.size = size
        ob = link(bpy.data.objects.new(name, data))
        ob.location = loc
        ob.rotation_euler = (Vector((0, 0, 1.0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        return ob

    area("Key", (2.5, -3.0, 3.2), 300, (1.0, 0.95, 0.9), 2.0)
    area("Fill", (-3.0, -2.0, 1.6), 90, (0.8, 0.85, 1.0), 3.0)
    area("Rim", (-1.2, 3.2, 2.8), 350, (0.6, 0.7, 1.0), 1.5)

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    if not world.node_tree:
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.36, 0.40, 0.50, 1.0)
        bg.inputs["Strength"].default_value = 0.35

    set_engine(scene, "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT")
    scene.view_settings.view_transform = "Standard"  # keeps the toon colours punchy
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1250


def main(argv):
    global COL
    args = argv[argv.index("--") + 1:] if "--" in argv else []

    def arg(flag):
        return args[args.index(flag) + 1] if flag in args else None

    for name in ("Sasuke", "Sasuke Stage"):
        old = bpy.data.collections.get(name)
        if old:
            for ob in list(old.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.collections.remove(old)
    for name in ("Cube", "Light", "Camera"):  # factory start-up scene
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)

    COL = bpy.data.collections.new("Sasuke")
    stage_col = bpy.data.collections.new("Sasuke Stage")
    bpy.context.scene.collection.children.link(COL)
    bpy.context.scene.collection.children.link(stage_col)

    build_materials()
    head = build_head()
    build_face(head)
    _, surf = build_hair(head)
    build_headband(surf)
    build_torso()
    build_arm(1)
    build_arm(-1)
    build_legs()
    setup_stage(stage_col)

    out_blend, out_png = arg("--out"), arg("--render")
    if out_blend:
        bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    if out_png:
        scene = bpy.context.scene
        if "--cpu" in args:  # for machines without a GPU/OpenGL context
            scene.render.engine = "CYCLES"
            scene.cycles.device = "CPU"
            scene.cycles.samples = int(arg("--samples") or 48)
            scene.cycles.use_denoising = True
        view = arg("--view")
        if view:  # "back", "front" or "face"
            cam = scene.camera
            target = Vector((0, 0, 1.3 if view == "face" else 0.9))
            cam.location = {"back": Vector((-1.9, 5.0, 1.55)), "front": Vector((0, -5.2, 1.2)),
                            "face": Vector((0.5, -3.0, 1.4))}[view]
            cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = out_png
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main(sys.argv)
