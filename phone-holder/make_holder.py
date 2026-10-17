#!/usr/bin/env python3
"""Chair-back hook phone holder for the Galaxy S23 Ultra (parametric).

Coordinates (the part as it hangs on the chair):
    X  left/right along the backrest
    Y  across the backrest thickness   (phone side = -Y, hook lip side = +Y)
    Z  up; Z = 0 is the top edge of the backrest rail

Usage:
    python3 make_holder.py                 # writes stl/*.stl and images/*.png
    python3 make_holder.py --rail 16.5     # backrest thickness measured with calipers

The part is symmetric left/right, so the same STL works on either face of the
backrest: just turn the holder around when you hang it.
"""
import argparse
import os

import numpy as np
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))

# --- Galaxy S23 Ultra (Samsung spec: 163.4 x 78.1 x 8.9 mm) -----------------
PHONE_H, PHONE_W, PHONE_T = 163.4, 78.1, 8.9


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def _cradle(landscape, case_extra, gap, z2, wall_len=None, lip_len=None, bar=0.0,
            t_p=4.0, left_full=False, win_bottom=None, wall=3.0, lip_t=2.0, lip_o=2.2, ledge_h=6.0):
    """Phone pocket: back plate (with camera window), ledge, side walls and lips.

    Phone side is -Y, plate back face at y = -gap. z2 = top of the phone pocket,
    unless None: then the ledge bottom is placed at z = 0.
    wall_len / lip_len: walls / lips only this tall above the ledge (None = full height).
    bar: extend the plate this far above the pocket to close the camera window.
    t_p: back plate thickness. left_full: the -X wall and its lips run the full pocket height.
    win_bottom: lower edge of the camera window (default: 12 mm above the ledge).
    wall / lip_t / lip_o / ledge_h: wall thickness, lip thickness, lip overlap on the screen, ledge height.
    """
    fit = 1.0                    # total side play for the phone
    ph_x = (PHONE_H if landscape else PHONE_W) + case_extra   # phone extent along X
    ph_z = (PHONE_W if landscape else PHONE_H) + case_extra   # phone extent along Z
    ph_t = PHONE_T + 0.8 + case_extra
    Pw = ph_x + fit              # pocket width
    margin = 6.0                 # frame left around the camera window
    Wc = Pw + 2 * wall

    if z2 is None:
        z2 = ph_z + 0.6 + ledge_h
    z_l = z2 - (ph_z + 0.6)                          # ledge top = phone bottom
    y_plate_front = -gap - t_p
    y_f = y_plate_front - ph_t                       # phone front plane
    y_out = y_f - lip_t                              # outer face of the lips
    z_bot = z_l - ledge_h
    z_wall = z_l + wall_len if wall_len else z2
    z_lip = z_l + lip_len if lip_len else z_wall

    cradle = box(-Wc / 2, Wc / 2, y_plate_front, -gap, z_bot, z2 + bar)     # back plate
    cradle -= box(-(Pw / 2 - margin), Pw / 2 - margin, y_plate_front - 1, -gap + 1,
                  z_l + 12 if win_bottom is None else win_bottom, z2 + (0.0 if bar else 0.01))                      # camera window
    cradle += box(-Wc / 2, Wc / 2, y_f, y_plate_front + 0.01, z_bot, z_l)    # ledge
    for s in (-1, 1):
        xi, xo = s * Pw / 2, s * (Pw / 2 + wall)
        xl = s * (Pw / 2 - lip_o)
        full = left_full and s == -1
        cradle += box(min(xi, xo), max(xi, xo), y_out, y_plate_front + 0.01, z_bot, z2 if full else z_wall)  # side wall
        cradle += box(min(xl, xi), max(xl, xi), y_out, y_f + 0.01, z_bot, z2 if full else z_lip)             # lip

    if landscape:
        # phone is turned 90 deg CCW: buttons point up (open), USB-C faces +X.
        # keep only the lower part of the +X wall so the cable and S Pen are free.
        z_cut = z_l + 20.0
        cradle -= box(Pw / 2 - lip_o - 0.1, Wc / 2 + 1, y_out - 1, y_plate_front + 0.01, z_cut, z2 + 1)
    else:
        # USB-C / speaker / S Pen: open the ledge in the middle
        cradle -= box(-25, 25, y_out - 1, y_plate_front + 0.01, z_bot - 1, z_l + 0.01)
        # power + volume keys on the +X side: open a window in that wall
        top_off, btn_len = 25.0, 80.0
        cradle -= box(Pw / 2 - lip_o - 0.1, Wc / 2 + 1, y_out - 1, y_plate_front + 0.01,
                      z2 - top_off - btn_len, z2 - top_off)

    return cradle, dict(z_l=z_l, z2=z2, y_f=y_f, y_out=y_out, y_plate_front=y_plate_front,
                        Pw=Pw, Wc=Wc, ph_x=ph_x, ph_z=ph_z, ph_t=ph_t, z_bot=z_bot, t_p=t_p)


def build(rail_t=10.0, orientation="portrait", gap=None, case_extra=0.0, hook_w=None):
    landscape = orientation == "landscape"

    # ---- hook (goes over the top of the backrest) -------------------------
    slot = rail_t + 1.6          # 1.6 mm total play; 1.3 mm pads in the 0.8 mm pockets take it up
    t_a, t_b, t_top = 4.0, 3.5, 4.0   # phone-side plate / lip-side leg / bridge thickness
    hook_len = 42.0              # how far the phone-side plate runs down the rail face
    b_len = 40.0                 # lip-side leg length
    ramp = 16.0                  # transition from hook width to cradle width
    pad_depth = 0.8
    hw = hook_w or (70.0 if landscape else 56.0)
    if gap is None:
        gap = 8.0 if landscape else 3.0   # stand-off so a bowed backrest never touches the cradle

    t_p = 4.0                    # cradle back plate
    Wc = (PHONE_H if landscape else PHONE_W) + case_extra + 1.0 + 2 * 3.0   # cradle outer width

    # ---------- hook ----------
    hook = box(-hw / 2, hw / 2, -t_a, 0, -hook_len, t_top)                 # phone-side plate
    hook += box(-hw / 2, hw / 2, -t_a, slot + t_b, 0, t_top)               # bridge
    hook += box(-hw / 2, hw / 2, slot, slot + t_b, -b_len, t_top)           # lip-side leg
    # felt-pad pockets
    hook -= box(-15, 15, slot - 0.01, slot + pad_depth, -b_len + 8, -8)
    hook -= box(-15, 15, -pad_depth, 0.01, -hook_len + 6, -6)

    # ---------- ramp from hook plate to cradle plate ----------
    z1 = -hook_len
    z2 = z1 - ramp                                   # top of the phone pocket
    pts = []
    for x in (-hw / 2, hw / 2):
        for y in (-t_a, 0):
            pts.append([x, y, z1])
    for x in (-Wc / 2, Wc / 2):
        for y in (-gap - t_p, -gap):
            pts.append([x, y, z2])
    ramp_body = Manifold.hull_points(pts)

    # ---------- cradle ----------
    cradle, c = _cradle(landscape, case_extra, gap, z2)
    z_l, y_f, y_out, Pw, Wc = c["z_l"], c["y_f"], c["y_out"], c["Pw"], c["Wc"]
    ph_x, ph_z, ph_t = c["ph_x"], c["ph_z"], c["ph_t"]

    part = hook + ramp_body + cradle
    meta = dict(slot=slot, z2=z2, z_l=z_l, y_f=y_f, y_out=y_out, gap=gap, hw=hw, Wc=Wc,
                Pw=Pw, ph_x=ph_x, ph_z=ph_z, ph_t=ph_t, t_a=t_a, t_b=t_b, b_len=b_len,
                hook_len=hook_len, landscape=landscape)
    return part, meta


def build_perch(rail_t=10.0, orientation="portrait", tilt=15.0, rise=0.0, case_extra=0.0, hook_w=None):
    """v2: the phone stands ON TOP of the backrest, leaning back, so nothing sticks out over the seat.

    Same coordinates as build(): Z = 0 is the rail top, the user / laptop is on the -Y side,
    the phone faces -Y and leans back (top toward +Y) by `tilt` degrees. `rise` lifts the
    phone further above the rail (mm) to clear a tall laptop screen.
    """
    landscape = orientation == "landscape"
    slot = rail_t + 1.6
    t_a, t_b, t_top = 4.0, 3.5, 5.0
    leg_len = 36.0
    pad_depth = 0.8
    hw = hook_w or (70.0 if landscape else 60.0)

    # ---- clip over the rail ----
    hook = box(-hw / 2, hw / 2, -t_a, slot + t_b, 0, t_top)                  # bridge
    hook += box(-hw / 2, hw / 2, -t_a, 0, -leg_len, t_top)                   # user-side leg
    hook += box(-hw / 2, hw / 2, slot, slot + t_b, -leg_len, t_top)          # back leg
    hook -= box(-15, 15, slot - 0.01, slot + pad_depth, -leg_len + 7, -7)    # felt pockets
    hook -= box(-15, 15, -pad_depth, 0.01, -leg_len + 7, -7)

    # ---- cradle in local coords (ledge bottom at z=0, plate back face at y=0) ----
    cradle, c = _cradle(landscape, case_extra, 0.0, None, wall_len=48.0, lip_len=34.0, bar=8.0)
    th = np.radians(tilt)

    def place_pts(y, z):
        # rotate about X so the top leans back (+Y); same as Manifold.rotate([-tilt, 0, 0])
        return y * np.cos(th) + z * np.sin(th), -y * np.sin(th) + z * np.cos(th)

    # put the phone's centre of mass (y) over the middle of the rail
    yc, zc = place_pts(-c["t_p"] - c["ph_t"] / 2, c["z_l"] + c["ph_z"] / 2)
    y_p = slot / 2 - yc
    z_p = t_top - 1.0 + rise
    def place(m):
        return m.rotate([-tilt, 0, 0]).translate([0, y_p, z_p])

    depth = c["t_p"] + c["ph_t"] + 2.0                # footprint of the cradle base
    d_fill = depth if rise <= 0 else 6.0
    post_w = hw if rise <= 0 else min(hw, 32.0)
    base = box(-post_w / 2, post_w / 2, -d_fill, 0, 0, 0.01)
    patch = box(-post_w / 2, post_w / 2, y_p - d_fill - 1, y_p + 1, t_top - 1.0, t_top)
    pts = []
    for m in (place(base), patch):
        v, _ = to_numpy(m)
        pts.extend(v.tolist())
    filler = Manifold.hull_points(pts)

    part = hook + filler + place(cradle)
    meta = dict(slot=slot, y_f=0, ph_x=c["ph_x"], ph_z=c["ph_z"], ph_t=c["ph_t"], z_l=c["z_l"],
                c=c, place=place, tilt=tilt, y_p=y_p, z_p=z_p, hw=hw, landscape=landscape)
    return part, meta


def to_numpy(m):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(float)
    f = np.asarray(mesh.tri_verts).astype(int)
    return v, f


def write_stl(m, path, print_orientation=True, rot=None):
    """Binary STL. print_orientation: lay the part on its side (X up) so the hook needs no supports."""
    if rot is not None:
        m = m.rotate(list(rot))
    elif print_orientation:
        m = m.rotate([0, 90, 0])
    bb = m.bounding_box()
    m = m.translate([-(bb[0] + bb[3]) / 2, -(bb[1] + bb[4]) / 2, -bb[2]])
    v, f = to_numpy(m)
    tri = v[f]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, tri
    with open(path, "wb") as fh:
        fh.write(b"capybara phone-holder".ljust(80, b"\0"))
        fh.write(np.uint32(len(f)).tobytes())
        fh.write(rec.tobytes())
    return m


def render(m, path, views, title="", ghosts=()):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    v, f = to_numpy(m)
    tri = v[f]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    light = np.array([0.4, -0.7, 0.6]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(nrm @ light, 0, 1)
    cols = np.stack([0.80 * shade, 0.55 * shade, 0.30 * shade, np.ones_like(shade)], 1)
    fig = plt.figure(figsize=(5 * len(views), 7))
    for i, (elev, azim) in enumerate(views):
        ax = fig.add_subplot(1, len(views), i + 1, projection="3d")
        pc = Poly3DCollection(tri, facecolors=cols, edgecolor="none")
        ax.add_collection3d(pc)
        for g, rgba in ghosts:
            gv, gf = to_numpy(g)
            ax.add_collection3d(Poly3DCollection(gv[gf], facecolors=[rgba], edgecolor=(0, 0, 0, 0.25), linewidths=0.3))
        mn, mx = v.min(0), v.max(0)
        c, r = (mn + mx) / 2, (mx - mn).max() / 2
        ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def phone_ghost(meta):
    """The phone as a box in the same frame as the holder."""
    if "place" in meta:                                   # v2 perch: local frame -> placed
        c = meta["c"]
        ph = box(-c["ph_x"] / 2, c["ph_x"] / 2, c["y_plate_front"] - PHONE_T, c["y_plate_front"],
                 c["z_l"], c["z_l"] + c["ph_z"])
        return meta["place"](ph)
    return box(-meta["ph_x"] / 2, meta["ph_x"] / 2, meta["y_f"], meta["y_f"] + meta["ph_t"],
               meta["z_l"], meta["z_l"] + meta["ph_z"])


def check(m, meta, rail_t):
    """Sanity checks: watertight, phone fits, backrest fits, nothing collides."""
    ph = phone_ghost(meta)
    rail = box(-200, 200, 0, rail_t, -100, 0)        # 400 x 100 mm backrest slab
    out = {
        "phone_collision_mm3": round((m ^ ph).volume(), 3),
        "rail_collision_mm3": round((m ^ rail).volume(), 3),
        "status": str(m.status()),
        "volume_cm3": round(m.volume() / 1000, 1),
        "bbox": [round(x, 1) for x in m.bounding_box()],
    }
    below = m.trim_by_plane([0, 0, -1], 0.0)             # everything below the rail top
    bb = below.bounding_box()
    out["below_rail_top: y_min / y_max (mm; rail front face is y=0)"] = [round(bb[1], 1), round(bb[4], 1)]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rail", type=float, default=10.0, help="backrest thickness in mm (measure it!)")
    ap.add_argument("--case", type=float, default=0.0, help="extra mm for a phone case")
    ap.add_argument("--gap", type=float, default=None, help="v1 only: stand-off between backrest and cradle")
    ap.add_argument("--tilt", type=float, default=15.0, help="v2: lean-back angle of the phone in degrees")
    ap.add_argument("--rise", type=float, default=0.0, help="v2: lift the phone this many mm above the rail top")
    a = ap.parse_args()

    os.makedirs(os.path.join(HERE, "stl"), exist_ok=True)
    os.makedirs(os.path.join(HERE, "images"), exist_ok=True)
    for orient in ("portrait", "landscape"):
        part, meta = build(a.rail, orient, a.gap, a.case)
        print(orient, check(part, meta, a.rail))
        write_stl(part, os.path.join(HERE, "stl", f"s23ultra_holder_{orient}_print.stl"))
        render(part, os.path.join(HERE, "images", f"{orient}.png"),
               [(18, -35), (18, 145), (0, -90)], f"S23 Ultra holder - {orient} (as hung; phone side = -Y)")

    # v2: phone on top of the backrest, nothing over the seat
    for orient in ("portrait", "landscape"):
        part, meta = build_perch(a.rail, orient, a.tilt, a.rise, a.case)
        print("perch", orient, check(part, meta, a.rail))
        write_stl(part, os.path.join(HERE, "stl", f"s23ultra_perch_{orient}_print.stl"))
        rail = box(-120, 120, 0, a.rail, -110, 0)
        render(part, os.path.join(HERE, "images", f"perch_{orient}.png"),
               [(15, -40), (0, 0), (15, 140)],
               f"Top-perch holder - {orient}  (user / laptop on the -Y side)",
               ghosts=[(phone_ghost(meta), (0.1, 0.1, 0.15, 0.35)), (rail, (0.35, 0.2, 0.1, 0.35))])
