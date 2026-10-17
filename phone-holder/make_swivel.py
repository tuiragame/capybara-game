#!/usr/bin/env python3
"""v3: swivel version of the top-perch holder - the phone turns between portrait and landscape.

Two printed parts + one M5x16 button-head screw and one M5 nut:
  clip   : clamp over the backrest + strut + round head (nut slot, stop peg)
  cradle : phone tray with a round back plate that turns on the head

The pivot is at the centre of the phone, so the phone + tray are balanced and stay wherever you
leave them. A stop peg limits the turn to 0 .. 90 deg counter-clockwise (portrait -> landscape).
In landscape the left wall of the tray (full length) carries the phone and the ledge ends up on
the right, so the USB-C notch faces the cable side.

    python3 make_swivel.py [--rail 10] [--clear 0] [--tilt 15] [--case 0]

Same coordinates as make_holder.py: Z = 0 is the rail top, the user / laptop is on the -Y side.
"""
import argparse
import math
import os

import numpy as np
from manifold3d import CrossSection, Manifold

from make_holder import HERE, PHONE_H, PHONE_T, PHONE_W, _cradle, box, render, to_numpy, write_stl

T_P = 6.0            # cradle back plate (thick enough for the screw-head counterbore)
HEAD_R = 28.0        # radius of the round head on the clip
HEAD_GAP = 0.3       # clearance between cradle plate and head before the screw is tightened
PSI_P = 20.0         # polar angle of the stop peg (degrees, in the plane of the plate)
PEG_R, PEG_ORBIT = 3.0, 15.0


def cyl_y(r, y0, y1, x=0.0, z=0.0, seg=64):
    """Cylinder along +Y from y0 to y1, centred on (x, z)."""
    c = Manifold.cylinder(y1 - y0, r, r, seg).rotate([-90, 0, 0])      # +Z -> +Y
    return c.translate([x, y0, z])


def sector_y(r0, r1, a0, a1, y0, y1, n=48):
    """Annular sector in the XZ plane (angles in degrees, counter-clockwise seen from the front)."""
    angs = np.radians(np.linspace(a0, a1, n))
    outer = [(r1 * np.cos(a), -r1 * np.sin(a)) for a in angs]            # 2-D y = -z (see rotate below)
    inner = [(r0 * np.cos(a), -r0 * np.sin(a)) for a in angs[::-1]]
    cs = CrossSection([np.array((outer + inner)[::-1], float)])   # counter-clockwise in 2-D
    m = Manifold.extrude(cs, y1 - y0).rotate([-90, 0, 0])
    return m.translate([0, y0, 0])


def build_swivel(rail_t=10.0, tilt=15.0, clear=0.0, case_extra=0.0, hw=60.0, strut_w=30.0):
    slot = rail_t + 1.6
    t_a, t_b, t_top, leg_len, pad_depth = 4.0, 3.5, 5.0, 36.0, 0.8

    # ---- cradle (local frame: hub centre = origin, plate back face at y = 0, phone toward -y) ----
    ph_z = PHONE_H + case_extra
    zc = 6.0 + ph_z / 2                                   # phone centre above the ledge bottom
    cradle, c = _cradle(False, case_extra, 0.0, None, wall_len=48.0, lip_len=34.0, bar=8.0,
                        t_p=T_P, left_full=True, win_bottom=6.0 + ph_z / 2 + 18.0)
    cradle = cradle.translate([0, 0, -zc])
    pad = math.degrees(math.asin(PEG_R / PEG_ORBIT)) + math.degrees(0.4 / PEG_ORBIT)
    cradle -= cyl_y(2.85, -T_P - 1, 1, seg=32)                                   # M5 clearance
    cradle -= cyl_y(5.2, -T_P - 0.01, -T_P + 3.2, seg=48)                        # button-head recess
    cradle -= sector_y(PEG_ORBIT - 3.4, PEG_ORBIT + 3.4, PSI_P - 90 - pad, PSI_P + pad, -2.8, 0.01)  # stop groove

    # ---- head (local frame, same origin) ----
    y_h0, y_h1 = HEAD_GAP, 8.0
    head = cyl_y(HEAD_R, y_h0, y_h1)
    head -= cyl_y(2.85, y_h0 - 1, y_h1 + 1, seg=32)
    nut = Manifold.cylinder(4.2, 4.75, 4.75, 6).rotate([0, 0, 30]).rotate([-90, 0, 0]).translate([0, y_h1 - 4.0, 0])
    head -= nut
    head -= box(-4.15, 4.15, y_h1 - 4.0, y_h1 + 0.01, 0, HEAD_R + 1)           # nut slides in from the top
    head += cyl_y(PEG_R, -2.4, y_h0 + 0.1, x=PEG_ORBIT * math.cos(math.radians(PSI_P)),
                  z=PEG_ORBIT * math.sin(math.radians(PSI_P)), seg=24)       # stop peg

    # ---- placement ----
    th = math.radians(tilt)
    com_y = -(T_P + c["ph_t"] / 2) * math.cos(th)         # phone centre of mass, relative to the pivot
    y_o = slot / 2 - com_y                                # put it right over the middle of the rail

    def at(m, z_o):
        return m.rotate([-tilt, 0, 0]).translate([0, y_o, z_o])

    def swung(beta):                                      # cradle turned CCW by beta degrees
        return cradle.rotate([0, -beta, 0])

    min_z = min(at(swung(b), 0.0).bounding_box()[2] for b in range(0, 91, 5))
    z_o = clear - min_z                                   # lowest point of the sweep = `clear` above the rail top

    # ---- clip: clamp + strut + head ----
    clip = box(-hw / 2, hw / 2, -t_a, slot + t_b, 0, t_top)
    clip += box(-hw / 2, hw / 2, -t_a, 0, -leg_len, t_top)
    clip += box(-hw / 2, hw / 2, slot, slot + t_b, -leg_len, t_top)
    clip -= box(-15, 15, slot - 0.01, slot + pad_depth, -leg_len + 7, -7)
    clip -= box(-15, 15, -pad_depth, 0.01, -leg_len + 7, -7)

    top_patch = at(box(-strut_w / 2, strut_w / 2, 4.2, 7.8, -24, -12), z_o)
    bot_patch = box(-strut_w / 2, strut_w / 2, slot / 2 - 6, slot / 2 + 6, t_top - 1.0, t_top)
    pts = []
    for m in (top_patch, bot_patch):
        v, _ = to_numpy(m)
        pts.extend(v.tolist())
    strut = Manifold.hull_points(pts)
    head_w = at(head, z_o)
    # keep the strut out of the nut slot / screw tip area
    clip = clip + strut + head_w

    phone_local = box(-c["ph_x"] / 2, c["ph_x"] / 2, -T_P - PHONE_T, -T_P, c["z_l"] - zc, c["z_l"] - zc + ph_z)
    meta = dict(c=c, z_o=z_o, y_o=y_o, tilt=tilt, slot=slot, at=lambda m: at(m, z_o), swung=swung,
                phone_local=phone_local, zc=zc, head_local=head, cradle_local=cradle)
    return clip, cradle, meta


def check(clip, cradle, meta, rail_t):
    at, swung = meta["at"], meta["swung"]
    rail = box(-200, 200, 0, rail_t, -110, 0)
    solid = clip + rail
    res = {}
    for beta in (0, 45, 90):
        res[f"collision@{beta}deg (mm3)"] = round((at(swung(beta)) ^ solid).volume(), 3)
    res["peg stops turn past 0 deg (mm3, expect >0)"] = round((at(swung(-6)) ^ clip).volume(), 3)
    res["peg stops turn past 90 deg (mm3, expect >0)"] = round((at(swung(96)) ^ clip).volume(), 3)
    res["phone@90 hits clip (mm3)"] = round((at(swung(90)) ^ clip).volume(), 3)
    phone = at(meta["phone_local"].rotate([0, -90, 0]))
    res["phone@90 hits clip/rail (mm3)"] = round((phone ^ solid).volume(), 3)
    res["lowest sweep point above rail top (mm)"] = round(min(at(swung(b)).bounding_box()[2] for b in range(0, 91, 5)), 1)
    res["pivot height above rail top (mm)"] = round(meta["z_o"], 1)
    res["clip components"] = len(clip.decompose())
    res["clip bbox"] = [round(x, 1) for x in clip.bounding_box()]
    res["cradle components"] = len(cradle.decompose())
    res["clip volume cm3"] = round(clip.volume() / 1000, 1)
    res["cradle volume cm3"] = round(cradle.volume() / 1000, 1)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rail", type=float, default=10.0, help="backrest thickness in mm (measure it!)")
    ap.add_argument("--clear", type=float, default=0.0,
                    help="lowest point the turning tray reaches, in mm above the rail top (keep >= 0, lower values hit the clip)")
    ap.add_argument("--tilt", type=float, default=15.0)
    ap.add_argument("--case", type=float, default=0.0)
    a = ap.parse_args()

    clip, cradle, meta = build_swivel(a.rail, a.tilt, a.clear, a.case)
    report = check(clip, cradle, meta, a.rail)
    for k, v in report.items():
        print(f"{k}: {v}")
    if any(report[f"collision@{b}deg (mm3)"] > 0.5 for b in (0, 45, 90)) or report["phone@90 hits clip (mm3)"] > 0.5:
        raise SystemExit("ERROR: the turning tray hits the clip - use a larger --clear (>= 0); nothing written")

    os.makedirs(os.path.join(HERE, "stl"), exist_ok=True)
    write_stl(clip, os.path.join(HERE, "stl", "s23ultra_swivel_clip_print.stl"), rot=(0, 90, 0))
    write_stl(cradle, os.path.join(HERE, "stl", "s23ultra_swivel_cradle_print.stl"), rot=(-90, 0, 0))

    rail = box(-120, 120, 0, a.rail, -110, 0)
    for name, beta in (("portrait", 0), ("landscape", 90)):
        shown = clip + meta["at"](meta["swung"](beta))
        phone = meta["at"](meta["phone_local"].rotate([0, -beta, 0]))
        render(shown, os.path.join(HERE, "images", f"swivel_{name}.png"),
               [(15, -40), (0, 0), (15, 140)], f"Swivel holder - {name}",
               ghosts=[(phone, (0.1, 0.1, 0.15, 0.35)), (rail, (0.35, 0.2, 0.1, 0.35))])
