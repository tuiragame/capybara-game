#!/usr/bin/env python3
"""Build phone-holder/s23ultra_holder.blend (and a preview render) with Blender's bpy module.

    pip install bpy manifold3d numpy
    python3 make_blend.py [--rail 18] [--case 0]

Scene units are millimetres (1 Blender unit = 1 mm). Each variant holds:
  Holder_*   the printable "top-perch" mesh as it sits on the chair (rail top = Z 0, user/laptop on the -Y side)
  Phone_*    ghost S23 Ultra, to check the fit
  Rail_*     ghost backrest slab of the thickness you passed in
The ghost objects live in the "Fit check" collection - hide it before exporting STL.
"""
import argparse
import math
import os

import bpy
from mathutils import Vector

from make_holder import box, build_perch, phone_ghost, to_numpy
from make_swivel import build_swivel

HERE = os.path.dirname(os.path.abspath(__file__))


def mesh_object(name, verts, faces, collection, material):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(material)
    collection.objects.link(ob)
    return ob


def material(name, rgba, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgba[:3], alpha)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgba[:3], 1)
    bsdf.inputs["Alpha"].default_value = alpha
    if alpha < 1:
        m.surface_render_method = "BLENDED"
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rail", type=float, default=18.0)
    ap.add_argument("--case", type=float, default=0.0)
    ap.add_argument("--tilt", type=float, default=15.0)
    ap.add_argument("--rise", type=float, default=0.0)
    ap.add_argument("--clear", type=float, default=0.0, help="swivel: lowest point of the turning tray above the rail top")
    ap.add_argument("--render", action="store_true", help="also write images/blender_preview.png (needs EGL/GPU libs)")
    a = ap.parse_args()

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001
    scene.unit_settings.length_unit = "MILLIMETERS"

    holders = bpy.data.collections.new("Holders")
    fit = bpy.data.collections.new("Fit check")
    scene.collection.children.link(holders)
    scene.collection.children.link(fit)

    m_holder = material("PETG", (0.95, 0.55, 0.15))
    m_phone = material("Phone ghost", (0.08, 0.08, 0.10), 0.55)
    m_rail = material("Walnut ghost", (0.28, 0.15, 0.08), 0.75)

    for i, orient in enumerate(("portrait", "landscape")):
        part, meta = build_perch(a.rail, orient, a.tilt, a.rise, a.case)
        v, f = to_numpy(part)
        dx = i * 260.0
        v = v + [dx, 0, 0]
        mesh_object(f"Holder_{orient}", v, f, holders, m_holder)

        pv, pf = to_numpy(phone_ghost(meta))
        mesh_object(f"Phone_{orient}", pv + [dx, 0, 0], pf, fit, m_phone)

        rv, rf = to_numpy(box(-170, 170, 0, a.rail, -110, 0))
        mesh_object(f"Rail_{orient}", rv + [dx, 0, 0], rf, fit, m_rail)

    # ---- v3 swivel: clip is static, the cradle + phone hang under an empty you can rotate ----
    clip, cradle, sm = build_swivel(a.rail, a.tilt, a.clear, a.case)
    dx = 520.0
    cv, cf = to_numpy(clip)
    mesh_object("Swivel_clip", cv + [dx, 0, 0], cf, holders, m_holder)
    tilt_frame = bpy.data.objects.new("Swivel_tilt_frame", None)
    tilt_frame.empty_display_type = "ARROWS"
    tilt_frame.empty_display_size = 40
    tilt_frame.location = (dx, sm["y_o"], sm["z_o"])
    tilt_frame.rotation_euler = (-math.radians(a.tilt), 0, 0)
    holders.objects.link(tilt_frame)
    turn = bpy.data.objects.new("Swivel_turn (rotate local Y)", None)
    turn.empty_display_type = "CIRCLE"
    turn.empty_display_size = 60
    turn.parent = tilt_frame
    holders.objects.link(turn)
    kv, kf = to_numpy(cradle)
    ob = mesh_object("Swivel_cradle", kv, kf, holders, m_holder)
    ob.parent = turn
    pv, pf = to_numpy(sm["phone_local"])
    ob = mesh_object("Swivel_phone", pv, pf, fit, m_phone)
    ob.parent = turn
    rv, rf = to_numpy(box(-170, 170, 0, a.rail, -110, 0))
    mesh_object("Swivel_rail", rv + [dx, 0, 0], rf, fit, m_rail)
    # turn portrait -> landscape (counter-clockwise from the front) over 50 frames
    turn.rotation_euler = (0, 0, 0)
    turn.keyframe_insert("rotation_euler", frame=1)
    turn.rotation_euler = (0, -math.pi / 2, 0)
    turn.keyframe_insert("rotation_euler", frame=50)
    turn.rotation_euler = (0, 0, 0)
    scene.frame_start, scene.frame_end = 1, 50

    # camera + Workbench preview settings
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 980
    cam = bpy.data.objects.new("Cam", cam_data)
    scene.collection.objects.link(cam)
    target = Vector((260, 0, 0))
    cam.location = target + Vector((330, -520, 230))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("W")
    scene.world.color = (0.93, 0.93, 0.95)
    scene.render.filepath = os.path.join(HERE, "images", "blender_preview.png")
    if a.render:
        bpy.ops.render.render(write_still=True)

    out = os.path.join(HERE, "s23ultra_holder.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("saved", out)


if __name__ == "__main__":
    main()
