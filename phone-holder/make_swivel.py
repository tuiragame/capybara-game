#!/usr/bin/env python3
"""v3 swivel holder, tough edition - curved clamp for a bowed backrest, phone turns portrait <-> landscape.

Parts (all printable):
  clip    clamp that follows the curve of the backrest + wide strut + round head
  cradle  phone tray with a round back plate that turns on the head
  knob    (printed-fastener version only) coin-slot knob with a coarse printed thread
or, instead of the printed knob, one M5 x 20 button-head screw + M5 nut (screw version).

    python3 make_swivel.py [--rail 10] [--radius 500] [--clear 0] [--tilt 15] [--case 4 | --case-dims W H T]

--radius is the radius of the FRONT (seat-side, concave) face of the backrest in mm. Measure it:
lay a straight edge across the front face over 200 mm and measure the gap s at the middle:
radius = 200^2 / (8 s) + s / 2.   (s = 10 mm -> 500 mm.)  0 = flat backrest.

Coordinates as in make_holder.py: Z = 0 is the rail top, user / laptop on the -Y side. The clamp is
curved in plan view; the user-side leg touches the concave face, so do not flip it around.
"""
import argparse
import math
import os

import numpy as np
from manifold3d import CrossSection, Manifold

from make_holder import HERE, PHONE_H, PHONE_T, PHONE_W, _cradle, box, render, to_numpy, write_stl

# ---- toughness-driven dimensions (mm) -------------------------------------------------------
T_A, T_B, T_TOP, LEG = 5.0, 5.0, 6.0, 40.0   # user-side leg, back leg, bridge, leg length
CLAMP_W = 70.0                                # clamp width along the (curved) backrest
STRUT_W = 44.0                                # strut width (was 30)
T_P = 8.0                                     # cradle back plate
HEAD_R, HEAD_Y0, HEAD_Y1 = 30.0, 0.3, 10.0    # round head (front face at y=0.3, 0.3 mm play)
PSI_P = 20.0                                  # polar angle of the stop peg
PEG_R, PEG_ORBIT, GROOVE_D = 3.5, 24.0, 3.0   # stop peg radius / orbit radius / groove depth
KNOB_R, KNOB_T = 16.0, 4.0
THREAD = dict(r=7.0, e=1.0, pitch=4.0, clr=0.4)   # twisted eccentric-circle thread: 6..8 mm radius, 4 mm pitch
PLANK_SHIFT = 0.8                             # plank sits mid-slot: 0.8 mm play front and back


# ---- small helpers ---------------------------------------------------------------------------
def cyl_y(r, y0, y1, x=0.0, z=0.0, seg=64):
    """Cylinder along +Y from y0 to y1, centred on (x, z)."""
    c = Manifold.cylinder(y1 - y0, r, r, seg).rotate([-90, 0, 0])      # +Z -> +Y
    return c.translate([x, y0, z])


def sector_y(r0, r1, a0, a1, y0, y1, n=48):
    """Annular sector in the XZ plane (angles in degrees, counter-clockwise seen from the front)."""
    angs = np.radians(np.linspace(a0, a1, n))
    outer = [(r1 * np.cos(a), -r1 * np.sin(a)) for a in angs]            # 2-D y = -z (see rotate below)
    inner = [(r0 * np.cos(a), -r0 * np.sin(a)) for a in angs[::-1]]
    cs = CrossSection([np.array((outer + inner)[::-1], float)])          # counter-clockwise in 2-D
    m = Manifold.extrude(cs, y1 - y0).rotate([-90, 0, 0])
    return m.translate([0, y0, 0])


def ccw(pts):
    a = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))
    return pts if a > 0 else pts[::-1]


def rect(u0, u1, z0, z1):
    return [(u0, z0), (u1, z0), (u1, z1), (u0, z1)]


def prof(pts):
    return CrossSection([np.array(ccw(pts), float)])


def arc_extrude(cs, R, width):
    """Sweep a (u, z) profile along the curved backrest. u = distance from the front (concave) face,
    z = height; centre of curvature at (0, -R). R <= 0 means flat."""
    R = R if R > 0 else 1e5
    ang = math.degrees(width / R)
    segs = int(max(360, math.ceil(8 * 360 / ang)))
    m = Manifold.revolve(cs.translate((R, 0)), segs, ang)
    return m.rotate([0, 0, 90 - ang / 2]).translate([0, -R, 0])


def slot_profile(slot, r):
    """Slot (void) between the legs, rounded top corners of radius r."""
    pts = [(0, -LEG - 1), (slot, -LEG - 1), (slot, -r)]
    pts += [(slot - r + r * math.cos(math.radians(t)), -r + r * math.sin(math.radians(t))) for t in np.linspace(0, 90, 10)[1:]]
    pts += [(r + r * math.cos(math.radians(t)), -r + r * math.sin(math.radians(t))) for t in np.linspace(90, 180, 10)[:-1]]
    pts += [(0, -r)]
    return pts


def clamp_body(rail_t, R, width):
    slot = rail_t + 2 * PLANK_SHIFT
    u = prof(rect(-T_A, slot + T_B, -LEG, T_TOP)) - prof(slot_profile(slot, 1.5))
    # lead-in chamfers on both leg tips
    u = u - prof([(0, -LEG), (0, -LEG + 3), (-1.5, -LEG)]) - prof([(slot, -LEG), (slot, -LEG + 3), (slot + 1.5, -LEG)])
    body = arc_extrude(u, R, width)
    pad = 0.8                                                           # felt / TPU pad pockets
    pw = max(width - 36.0 if width > 40 else width - 10.0, 14.0)
    body -= arc_extrude(prof(rect(-pad, 0.01, -LEG + 7, -7)), R, pw)
    body -= arc_extrude(prof(rect(slot - 0.01, slot + pad, -LEG + 7, -7)), R, pw)
    return body, slot


def twisted(r, e, length, pitch, y_start, extra_r=0.0):
    """Eccentric circle twisted along its axis = a coarse, V-ish thread. Runs along -Y from y_start."""
    cs = CrossSection.circle(r + extra_r, 48).translate((e, 0))
    twist = 360.0 * length / pitch
    m = Manifold.extrude(cs, length, int(math.ceil(abs(twist) / 5.0)), twist)
    return m.rotate([90, 0, 0]).translate([0, y_start, 0])


def thread_z(length, extra_r=0.0, z0=0.0):
    """Same thread, axis along +Z (for the stand-alone test print)."""
    t = THREAD
    cs = CrossSection.circle(t["r"] + extra_r, 48).translate((t["e"], 0))
    m = Manifold.extrude(cs, length, int(math.ceil(360.0 * length / t["pitch"] / 5.0)), 360.0 * length / t["pitch"])
    return m.translate([0, 0, z0])


def make_knob():
    """Knob in the cradle's local frame (axis = Y); its front face sits 0.4 mm below the plate front."""
    y_front, y_back = -T_P + 0.4, -T_P + 0.4 + KNOB_T
    k = cyl_y(KNOB_R, y_front, y_back)
    # same helix phase as the post (post starts at y = 3): start the hole a whole number of pitches away
    k -= twisted(THREAD["r"], THREAD["e"], 8.0, THREAD["pitch"], 3.0 - THREAD["pitch"], extra_r=THREAD["clr"])
    k -= box(-1.4, 1.4, y_front - 0.01, y_front + 1.8, -KNOB_R - 1, KNOB_R + 1)            # coin slot
    return k


# ---- the whole thing ---------------------------------------------------------------------------
def build_swivel(rail_t=10.0, tilt=15.0, clear=0.0, case_extra=4.0, radius=500.0, fastener="printed", margin=4.0):
    printed = fastener == "printed"
    ex = tuple(case_extra) if isinstance(case_extra, (tuple, list)) else (case_extra,) * 3
    ph_z = PHONE_H + ex[1]
    ledge_h = 8.0
    zc_pre = ledge_h + ph_z / 2
    cradle, c = _cradle(False, case_extra, 0.0, None, wall_len=48.0, lip_len=34.0, bar=8.0, t_p=T_P,
                        left_full=True, win_bottom=zc_pre + 18.0, wall=4.0, lip_t=2.5, lip_o=2.4, ledge_h=ledge_h)
    zc = c["z_l"] + ph_z / 2
    cradle = cradle.translate([0, 0, -zc])

    pad = math.degrees(math.asin(PEG_R / PEG_ORBIT)) + math.degrees(0.4 / PEG_ORBIT)
    cradle -= sector_y(PEG_ORBIT - PEG_R - 0.4, PEG_ORBIT + PEG_R + 0.4, PSI_P - 90 - pad, PSI_P + pad,
                       -GROOVE_D, 0.01)                                                  # stop groove
    if printed:
        cradle -= cyl_y(8.8, -T_P - 1, 1)                                               # clearance for the thread post
        cradle -= cyl_y(KNOB_R + 0.4, -T_P - 0.01, -T_P + 4.4)                          # recess for the knob
    else:
        cradle -= cyl_y(2.85, -T_P - 1, 1, seg=32)                                      # M5 clearance
        cradle -= cyl_y(5.2, -T_P - 0.01, -T_P + 3.2, seg=48)                           # button-head recess

    # ---- round head (local frame) ----
    head = cyl_y(HEAD_R, HEAD_Y0, HEAD_Y1)
    head += cyl_y(PEG_R, -GROOVE_D + 0.4, HEAD_Y0 + 0.1, x=PEG_ORBIT * math.cos(math.radians(PSI_P)),
                  z=PEG_ORBIT * math.sin(math.radians(PSI_P)), seg=32)                   # stop peg
    if printed:
        head += twisted(THREAD["r"], THREAD["e"], 10.4, THREAD["pitch"], 3.0)           # printed thread post
    else:
        head -= cyl_y(2.85, HEAD_Y0 - 1, HEAD_Y1 + 1, seg=32)
        nut = Manifold.cylinder(4.2, 4.75, 4.75, 6).rotate([0, 0, 30]).rotate([-90, 0, 0]).translate([0, HEAD_Y1 - 4.0, 0])
        head -= nut
        head -= box(-4.15, 4.15, HEAD_Y1 - 4.0, HEAD_Y1 + 0.01, 0, HEAD_R + 1)         # nut slides in from the top

    # ---- placement ----
    th = math.radians(tilt)
    com_y = -(T_P + c["ph_t"] / 2) * math.cos(th)
    clamp, slot = clamp_body(rail_t, radius, CLAMP_W)
    y_o = slot / 2 - com_y                                                              # phone CoM over the middle of the slot

    def at(m, z_o):
        return m.rotate([-tilt, 0, 0]).translate([0, y_o, z_o])

    def swung(beta):
        return cradle.rotate([0, -beta, 0])

    min_z = min(at(swung(b), 0.0).bounding_box()[2] for b in range(0, 91, 5))
    z_o = clear + margin - min_z      # lowest point of the sweep = `clear` + `margin` above the rail top

    top_patch = at(box(-STRUT_W / 2, STRUT_W / 2, 4.5, 13.0, -22, -12), z_o)
    bot_patch = box(-STRUT_W / 2, STRUT_W / 2, slot / 2 - 9, slot / 2 + 9, T_TOP - 1.0, T_TOP)
    pts = []
    for m in (top_patch, bot_patch):
        v, _ = to_numpy(m)
        pts.extend(v.tolist())
    strut = Manifold.hull_points(pts)
    clip = clamp + strut + at(head, z_o)

    phone_local = box(-c["ph_x"] / 2, c["ph_x"] / 2, -T_P - (c["ph_t"] - 0.8), -T_P, c["z_l"] - zc, c["z_l"] - zc + ph_z)
    knob = make_knob() if printed else None
    meta = dict(c=c, z_o=z_o, y_o=y_o, tilt=tilt, slot=slot, at=lambda m: at(m, z_o), swung=swung,
                phone_local=phone_local, zc=zc, radius=radius, rail_t=rail_t, printed=printed, clamp=clamp)
    return clip, cradle, knob, meta


def rail_ghost(rail_t, R, width=340.0, shift=PLANK_SHIFT):
    return arc_extrude(prof(rect(shift, shift + rail_t, -110, 0)), R, width)


def check(clip, cradle, knob, meta):
    at, swung = meta["at"], meta["swung"]
    R, t = meta["radius"], meta["rail_t"]
    rail = rail_ghost(t, R)
    solid = clip + rail
    res = {}
    res["tray vs clip/backrest, worst of 0..90 deg in 5 deg steps (mm3)"] = round(
        max((at(swung(b)) ^ solid).volume() for b in range(0, 91, 5)), 3)
    res["peg stops turn past 0 deg (mm3, expect >0)"] = round((at(swung(-6)) ^ clip).volume(), 3)
    res["peg stops turn past 90 deg (mm3, expect >0)"] = round((at(swung(96)) ^ clip).volume(), 3)
    phone = at(meta["phone_local"].rotate([0, -90, 0]))
    res["phone@90 hits clip/rail (mm3)"] = round((phone ^ solid).volume(), 3)
    res["lowest sweep point above rail top (mm)"] = round(min(at(swung(b)).bounding_box()[2] for b in range(0, 91, 5)), 1)
    res["pivot height above rail top (mm)"] = round(meta["z_o"], 1)
    # fit on a backrest whose real curvature differs from --radius
    for r_true in (R * 0.7, R * 1.5, 0):
        res[f"clamp vs plank of R={'flat' if r_true == 0 else round(r_true)} (mm3)"] = round(
            (meta["clamp"] ^ rail_ghost(t, r_true)).volume(), 2)
    res["clip pieces"] = len(clip.decompose())
    res["cradle pieces"] = len(cradle.decompose())
    res["clip bbox"] = [round(x, 1) for x in clip.bounding_box()]
    res["clip / cradle volume cm3"] = [round(clip.volume() / 1000, 1), round(cradle.volume() / 1000, 1)]
    if knob is not None:
        # the knob must move freely along the helix of the post: turn by phi and advance phi/360*pitch
        post = twisted(THREAD["r"], THREAD["e"], 10.4, THREAD["pitch"], 3.0)
        worst = 0.0
        for phi in range(0, 360, 30):
            moved = knob.rotate([0, -phi, 0]).translate([0, -THREAD["pitch"] * phi / 360.0, 0])
            worst = max(worst, (moved ^ post).volume())
        res["printed thread: knob vs post overlap over a full turn (mm3, expect 0)"] = round(worst, 3)
        res["printed thread: knob pushed straight 2 mm without turning (mm3, expect >0 = locked)"] = round(
            (knob.translate([0, -2.0, 0]) ^ post).volume(), 1)
        res["knob pieces"] = len(knob.decompose())
    return res


# ---- exports --------------------------------------------------------------------------------------
def tpu_pads():
    w, h = 33.0, 25.0
    return box(-w / 2, w / 2, 0, 1.3, 0, h) + box(-w / 2 + 40, w / 2 + 40, 0, 1.3, 0, h)


def thread_test(base_r=KNOB_R):
    off = 2 * base_r + 8
    post = Manifold.cylinder(4.0, base_r, base_r, 64) + thread_z(9.0, z0=3.5)
    knob = Manifold.cylinder(KNOB_T, KNOB_R, KNOB_R, 64).translate([off, 0, 0])
    knob -= thread_z(KNOB_T + 2, extra_r=THREAD["clr"], z0=-1).translate([off, 0, 0])
    knob -= box(off - 1.4, off + 1.4, -KNOB_R - 1, KNOB_R + 1, KNOB_T - 1.8, KNOB_T + 0.01)
    return post + knob


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rail", type=float, default=10.0, help="backrest thickness in mm (measure it!)")
    ap.add_argument("--radius", type=float, default=500.0,
                    help="radius of the backrest's front (concave) face in mm; 0 = flat (see the docstring to measure it)")
    ap.add_argument("--clear", type=float, default=0.0, help="lowest point of the turning tray above the rail top (>= 0)")
    ap.add_argument("--tilt", type=float, default=15.0)
    ap.add_argument("--case", type=float, default=4.0,
                    help="extra mm for a phone case, added to width, height and thickness (0 = bare phone)")
    ap.add_argument("--case-dims", type=float, nargs=3, metavar=("W", "H", "T"),
                    help="measured size of phone + case in mm (width height thickness); overrides --case")
    a = ap.parse_args()
    if a.case_dims:
        a.case = (a.case_dims[0] - PHONE_W, a.case_dims[1] - PHONE_H, a.case_dims[2] - PHONE_T)

    os.makedirs(os.path.join(HERE, "stl"), exist_ok=True)
    stl = lambda n: os.path.join(HERE, "stl", n)
    R_eff = a.radius if a.radius > 0 else 1e5
    ang = math.degrees(CLAMP_W / R_eff)
    results = {}
    for mode in ("printed", "screw"):
        clip, cradle, knob, meta = build_swivel(a.rail, a.tilt, a.clear, a.case, a.radius, mode)
        report = check(clip, cradle, knob, meta)
        print(f"== {mode}")
        for k, v in report.items():
            print(f"  {k}: {v}")
        bad = [report["tray vs clip/backrest, worst of 0..90 deg in 5 deg steps (mm3)"], report["phone@90 hits clip/rail (mm3)"]]
        if any(x > 0.05 for x in bad):
            raise SystemExit("ERROR: the turning tray hits the clip - use a larger --clear (>= 0); nothing written")
        # print orientation: clip on its side, flat on the clamp's end face; cradle back-down; knob back-down
        write_stl(clip.rotate([0, 0, ang / 2]), stl(f"v3_clip_{mode}_print.stl"), rot=(0, 90, 0))
        write_stl(cradle, stl(f"v3_cradle_{mode}_print.stl"), rot=(-90, 0, 0))
        if knob is not None:
            write_stl(knob, stl("v3_knob_print.stl"), rot=(-90, 0, 0))
        results[mode] = (clip, cradle, knob, meta)

    # small test prints
    fit, _ = clamp_body(a.rail, a.radius, 30.0)
    write_stl(fit.rotate([0, 0, math.degrees(30.0 / R_eff) / 2]), stl("test_clamp_fit_print.stl"), rot=(0, 90, 0))
    write_stl(thread_test(), stl("test_printed_thread_print.stl"), rot=(0, 0, 0))
    write_stl(tpu_pads(), stl("pads_tpu_print.stl"), rot=(-90, 0, 0))

    clip, cradle, knob, meta = results["printed"]
    rail = rail_ghost(a.rail, a.radius, 240.0)
    for name, beta in (("portrait", 0), ("landscape", 90)):
        shown = clip + meta["at"](meta["swung"](beta))
        phone = meta["at"](meta["phone_local"].rotate([0, -beta, 0]))
        render(shown, os.path.join(HERE, "images", f"swivel_{name}.png"),
               [(15, -40), (0, 0), (15, 140)], f"Swivel holder (tough edition) - {name}",
               ghosts=[(phone, (0.1, 0.1, 0.15, 0.35)), (rail, (0.35, 0.2, 0.1, 0.35))])


if __name__ == "__main__":
    main()
