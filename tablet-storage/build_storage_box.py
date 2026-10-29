#!/usr/bin/env python3
"""XPPen Deco Pro LW (Gen 2) 竖立收纳座 -> 3MF (Bambu Lab P1S).

平板、快捷键遥控器(ACK05)、数位笔全部「竖着插」,无盖,占地约 120 x 66 mm。

    俯视图 (y 向上 = 后方)
        ┌──────────────┐
        │   (  笔  )   │  <- 笔塔 (圆柱, 高 80)
        │ ┌──────────┐ │
        │ │ 平板槽   │ │  <- 平板立着插, 槽深 36, 两端贯通
        │ └──────────┘ │
        │   ┌──────┐   │
        │   │遥控器│   │  <- 遥控器短边朝下立着插
        │   └──────┘   │
        └──────────────┘

用法:  python3 build_storage_box.py            -> 完整版
       python3 build_storage_box.py --fit-test -> 低矮试配版 (很快打完)
所有尺寸单位 mm, 改下面的常量即可。
"""
import sys
import zipfile
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold

# ---- 设备尺寸 (官方规格 + 评测数据) -------------------------------------
TABLET_T = 10.7          # 平板厚度 10.66
KEYPAD_T = 10.0          # ACK05 厚度 10 (转盘处可能略厚, 槽留余量)
KEYPAD_H = 70.5          # ACK05 短边

# ---- 间隙 / 结构 ----------------------------------------------------------
TABLET_SLOT_W = TABLET_T + 1.7      # 12.4  (单边约 0.85)
KEYPAD_SLOT_W = KEYPAD_T + 4.0      # 14.0
KEYPAD_SLOT_L = KEYPAD_H + 5.5      # 76.0
PEN_HOLE_D = 20.0                   # 笔握持处最粗约 15~16
WALL = 5.0
PEN_WALL = 4.0
LEAD_IN = 1.5                       # 槽口导角
CORNER_R = 4.0

BASE_L = 120.0                      # 底座长度; 平板槽两端贯通, 平板(333)左右悬出
BASE_H = 45.0
SLOT_DEPTH = 40.0                   # 遥控器槽深度
TABLET_SLOT_DEPTH = 36.0            # 平板槽深度 (槽底留 9 mm 连接前后两块)
USB_SLOT_W = 26.0                   # U 盘槽 宽 (x), 一般 U 盘 / 接收器 <= 24
USB_SLOT_T = 14.0                   # U 盘槽 厚 (y), 一般 U 盘 <= 12
USB_SLOT_DEPTH = 35.0
USB_SLOT_CX = 24.0                  # 槽中心 x (笔塔左侧)
TOWER_H = 80.0
PEN_FLOOR = 6.0

FIT_TEST = "--fit-test" in sys.argv
if FIT_TEST:
    BASE_H, SLOT_DEPTH, TABLET_SLOT_DEPTH, TOWER_H, PEN_FLOOR = 12.0, 8.0, 8.0, 16.0, 4.0
    USB_SLOT_DEPTH = 8.0

L = BASE_L
# y: 前 -> 后
Y_KEYPAD0 = WALL
Y_TABLET0 = Y_KEYPAD0 + KEYPAD_SLOT_W + WALL
Y_TABLET1 = Y_TABLET0 + TABLET_SLOT_W
PEN_CY = Y_TABLET1 + WALL + PEN_HOLE_D / 2
PEN_OD = PEN_HOLE_D + 2 * PEN_WALL
BASE_W = PEN_CY + PEN_OD / 2 + 1.0   # 底座补满成长方形 (后排放笔塔与 U 盘槽), 笔塔后留 1 mm 避免相切
USB_CY = (Y_TABLET1 + BASE_W) / 2


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def lead_in_slot(x0, y0, x1, y1, z_top, depth):
    """矩形槽 + 顶部倒角导入口 (槽口比槽身大 LEAD_IN)。"""
    body = box(x0, y0, z_top - depth, x1, y1, z_top + 1)
    w, h = x1 - x0, y1 - y0
    cs = CrossSection.square((w, h), center=True)
    flare = Manifold.extrude(cs, LEAD_IN, scale_top=((w + 2 * LEAD_IN) / w, (h + 2 * LEAD_IN) / h))
    flare = flare.translate(((x0 + x1) / 2, (y0 + y1) / 2, z_top - LEAD_IN))
    return body + flare


def build():
    r = CORNER_R
    rect = CrossSection.square((L - 2 * r, BASE_W - 2 * r)).translate((r, r))
    rect = rect.offset(r, JoinType.Round, circular_segments=48)
    pen_circle = CrossSection.circle(PEN_OD / 2, 96).translate((L / 2, PEN_CY))
    body = Manifold.extrude(rect, BASE_H) + Manifold.extrude(pen_circle, TOWER_H - BASE_H).translate((0, 0, BASE_H))

    # 平板槽 (两端贯通)
    body -= lead_in_slot(-LEAD_IN - 1, Y_TABLET0, L + LEAD_IN + 1, Y_TABLET1, BASE_H, TABLET_SLOT_DEPTH)
    # 遥控器槽 (左右居中)
    kx0 = (L - KEYPAD_SLOT_L) / 2
    body -= lead_in_slot(kx0, Y_KEYPAD0, kx0 + KEYPAD_SLOT_L, Y_KEYPAD0 + KEYPAD_SLOT_W, BASE_H, SLOT_DEPTH)
    # U 盘槽 (后排, 笔塔左侧)
    body -= lead_in_slot(USB_SLOT_CX - USB_SLOT_W / 2, USB_CY - USB_SLOT_T / 2,
                         USB_SLOT_CX + USB_SLOT_W / 2, USB_CY + USB_SLOT_T / 2, BASE_H, USB_SLOT_DEPTH)
    # 笔孔 (带导角)
    hole = Manifold.cylinder(TOWER_H - PEN_FLOOR + 1, PEN_HOLE_D / 2, circular_segments=96)
    hole = hole.translate((L / 2, PEN_CY, PEN_FLOOR))
    cone = Manifold.cylinder(LEAD_IN, PEN_HOLE_D / 2, PEN_HOLE_D / 2 + LEAD_IN, circular_segments=96)
    cone = cone.translate((L / 2, PEN_CY, TOWER_H - LEAD_IN))
    body -= hole + cone
    return body


def write_3mf(manifold, path, name, plate_center=(128.0, 128.0)):
    m = manifold.to_mesh()
    v = np.asarray(m.vert_properties, dtype=np.float64)[:, :3]
    t = np.asarray(m.tri_verts, dtype=np.int64)
    lo, hi = v.min(0), v.max(0)
    v = v - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])   # 底面贴 z=0, xy 居中

    # 布尔运算会留下重合顶点 / 零面积三角形: 焊接到 0.1 um 并删掉退化面, 切片软件才不会报错
    tm = trimesh.Trimesh(np.round(v, 4), t, process=False)
    tm.merge_vertices()
    tm.update_faces(tm.area_faces > 1e-9)
    tm.remove_unreferenced_vertices()
    assert tm.is_watertight and tm.is_winding_consistent, "mesh not watertight"
    v, t = tm.vertices, tm.faces

    verts = "\n".join(f'     <vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in v)
    tris = "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t)
    model = f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
 <metadata name="Title">{name}</metadata>
 <resources>
  <object id="1" type="model" name="{name}">
   <mesh>
    <vertices>
{verts}
    </vertices>
    <triangles>
{tris}
    </triangles>
   </mesh>
  </object>
 </resources>
 <build>
  <item objectid="1" transform="1 0 0 0 1 0 0 0 1 {plate_center[0]} {plate_center[1]} 0"/>
 </build>
</model>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    return hi - lo


if __name__ == "__main__":
    out_dir = Path(__file__).parent
    body = build()
    assert body.status().name == "NoError", body.status()
    name = "deco_pro_lw_gen2_storage_fit_test" if FIT_TEST else "deco_pro_lw_gen2_storage"
    size = write_3mf(body, out_dir / f"{name}.3mf", name)
    print(f"{name}.3mf  size(mm)={size.round(1)}  volume={body.volume() / 1000:.1f} cm3")
