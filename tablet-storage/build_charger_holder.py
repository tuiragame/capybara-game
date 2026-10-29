#!/usr/bin/env python3
"""Chicony A21-200P2B (MSI Katana 17 B12V, 200W) 变压器收纳座 -> 3MF (Bambu Lab P1S).

变压器侧立插在中间的窄槽里, 无盖; 两条线(DC 线 + 电源线)直接绕在座子外圈的凹槽里, 所以占地很小。

    侧视图                          俯视图
      ┌──┐          ┌──┐             ┌────────────────────┐ 顶/底挡边
      │  │ 变压器   │  │             │ ┌────────────────┐ │
    ┌─┴──┴──────────┴──┴─┐           │ │   变压器槽     │ │  <- 槽两端有出线缺口
    ╞══ 绕线凹槽(深7) ════╡           │ └────────────────┘ │
    └────────────────────┘           └────────────────────┘

用法:  python3 build_charger_holder.py            -> 完整版
       python3 build_charger_holder.py --fit-test -> 低矮试配版
所有尺寸单位 mm, 改下面的常量即可。
"""
import sys
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold

from build_storage_box import box, write_3mf  # noqa: E402  (复用 3MF 写出与清理)

# ---- 变压器尺寸 (零售商数据, 取较大的一组) --------------------------------
BRICK_L, BRICK_W, BRICK_T = 147.3, 77.7, 25.3     # 长 x 高(立着时) x 厚

# ---- 结构 -----------------------------------------------------------------
SLOT_L = BRICK_L + 2.7             # 150  槽长 (x)
SLOT_T = BRICK_T + 2.7             # 28   槽宽 (y), 单边约 1.35
WALL = 4.0                         # 槽壁 (核心)
GROOVE = 7.0                       # 绕线凹槽深度 (线径含余量 <= 7)
FLANGE = 3.0                       # 顶挡边厚
BASE_FLANGE = 4.0                  # 底挡边厚
CHAMFER = GROOVE                   # 顶挡边下方 45° 过渡 (不需支撑)
FLOOR = 6.0                        # 槽底高度
WIND_H = 60.0                      # 直段绕线区高度 (两条线约需 52, 留余量)
SCOOP_R = 22.0                     # 两侧取放用的半圆缺口
SCOOP_BOTTOM = 46.0
NOTCH_W = 14.0                     # 两端出线缺口宽度 (DC 线护套)
NOTCH_BOTTOM = 34.0
VENT_W, VENT_Z0, VENT_Z1 = 6.0, 14.0, 40.0
VENT_X = [32.0, 46.0, 60.0]        # 散热缝中心 x (左右对称), 避开取放缺口

FIT_TEST = "--fit-test" in sys.argv
if FIT_TEST:
    WIND_H, FLOOR, NOTCH_BOTTOM = 8.0, 4.0, 12.0

H = BASE_FLANGE + WIND_H + CHAMFER + FLANGE
CORE_L, CORE_W = SLOT_L + 2 * WALL, SLOT_T + 2 * WALL
OUT_L, OUT_W = CORE_L + 2 * GROOVE, CORE_W + 2 * GROOVE


def rrect(l, w, r):
    cs = CrossSection.square((l - 2 * r, w - 2 * r), center=True)
    return cs.offset(r, JoinType.Round, circular_segments=48)


def build():
    outer, core = rrect(OUT_L, OUT_W, 8.0), rrect(CORE_L, CORE_W, 5.0)
    z_chamfer = BASE_FLANGE + WIND_H
    body = Manifold.extrude(outer, BASE_FLANGE)
    body += Manifold.extrude(core, z_chamfer + CHAMFER - BASE_FLANGE).translate((0, 0, BASE_FLANGE))
    body += Manifold.extrude(core, CHAMFER, scale_top=(OUT_L / CORE_L, OUT_W / CORE_W)).translate((0, 0, z_chamfer))
    body += Manifold.extrude(outer, FLANGE).translate((0, 0, H - FLANGE))

    # 变压器槽 (顶部带导角)
    lip = Manifold.extrude(CrossSection.square((SLOT_L, SLOT_T), center=True), 1.5,
                           scale_top=((SLOT_L + 3) / SLOT_L, (SLOT_T + 3) / SLOT_T)).translate((0, 0, H - 1.5))
    body -= box(-SLOT_L / 2, -SLOT_T / 2, FLOOR, SLOT_L / 2, SLOT_T / 2, H + 1) + lip
    # 两端出线缺口 (从顶面向下开口, 线可直接放入)
    for s in (-1, 1):
        x0, x1 = sorted((s * (SLOT_L / 2 - 1), s * (OUT_L / 2 + 1)))
        body -= box(x0, -NOTCH_W / 2, NOTCH_BOTTOM, x1, NOTCH_W / 2, H + 1)
    if not FIT_TEST:
        # 前后两侧取放缺口 (半圆, 露出变压器两个大面, 方便捏住)
        for s in (-1, 1):
            y0, y1 = sorted((s * (SLOT_T / 2 - 1), s * (OUT_W / 2 + 1)))
            scoop = Manifold.cylinder(y1 - y0, SCOOP_R, circular_segments=96).rotate((-90, 0, 0))
            scoop = scoop.translate((0, y0, SCOOP_BOTTOM + SCOOP_R))
            body -= scoop
            # 散热缝 (只开在核心壁上, 绕线从外面盖过不影响)
            for sx in (-1, 1):
                for vx in VENT_X:
                    body -= box(sx * vx - VENT_W / 2, y0, VENT_Z0, sx * vx + VENT_W / 2, y1, VENT_Z1)
    return body


if __name__ == "__main__":
    out_dir = Path(__file__).parent
    body = build()
    assert body.status().name == "NoError", body.status()
    name = "charger_holder_fit_test" if FIT_TEST else "charger_holder_a21_200p2b"
    size = write_3mf(body, out_dir / f"{name}.3mf", name)
    print(f"{name}.3mf  size(mm)={size.round(1)}  volume={body.volume() / 1000:.1f} cm3")
