"""三段式公司设施: 后室 x SCP x 致命公司。(4m 模块重写版)

实测: 墙段 4×1×4m, 地砖 4×4m, 格栅 4×2m(下沉), 柱 1.5×1.5×4m → 全部布局按 4m 网格。
  A 安检大厅   x[0..8]   y[0..8]   SCP: 观察窗+闸门+值班台
  B0 走廊      x[8..12]  y[0..4]
  B 后室迷宫   x[12..28] y[-8..8]  芥末黄 16×16, 十字内墙环形门洞, 极度空旷
  C0 转换走廊  x[20..24] y[8..12]  破墙过渡
  C 工业核心   x[12..28] y[12..28] LC: 钻探反应堆+警报塔+下沉格栅+战利品
产出 assets/maps/vendor/facility_three_zone.glb
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_corridor import load_template, place, delete_templates, TEMPLATES
from build_vendor_lc import filtered_gltf_export, ROOT, VENDOR

DGN = os.path.join(ROOT, "assets", "static", "vendor", "dungeon")
BK = os.path.join(ROOT, "assets", "static", "vendor", "backrooms")
FRN = os.path.join(ROOT, "assets", "static", "vendor", "furniture")
EV = os.path.join(ROOT, "assets", "static", "event")
SPK = os.path.join(ROOT, "assets", "static", "vendor", "space_dark")

OUT = os.path.join(ROOT, "assets", "maps", "vendor", "facility_three_zone.glb")

LOADS = [
    ("wall", "wall", DGN), ("wall_doorway", "wall_doorway", DGN),
    ("wall_broken", "wall_broken", DGN), ("wall_gated", "wall_gated", DGN),
    ("wall_window", "wall_window_closed", DGN),
    ("floor", "floor_tile_large", DGN), ("grate", "floor_tile_grate", DGN),
    ("pillar", "pillar", DGN),
    ("torch", "torch_lit", DGN), ("candle", "candle_triple", DGN),
    ("barrel", "barrel_large", DGN), ("crates", "crates_stacked", DGN),
    ("chest", "chest", DGN), ("table", "table_medium", DGN),
    ("chair", "chair", DGN), ("shelf", "shelf_large", DGN),
    ("rubble", "rubble_large", DGN), ("trunk", "trunk_medium_A", DGN),
    ("wall_y", "wall", BK), ("pillar_y", "pillar", BK),
    ("carpet", "floor_dirt_large", BK),
    ("cabinet", "cabinet_medium", FRN), ("lamp", "lamp_standing", FRN),
    ("armchair", "armchair", FRN),
    ("siren", "siren_tower", EV),
    ("reactor", "drill_structure", SPK),
]


def floor_grid(ux0, uy0, nx, ny, key="floor"):
    """按 4m 网格铺砖; ux0/uy0 为格单元坐标。"""
    size = TEMPLATES[key][3]
    for i in range(nx):
        for j in range(ny):
            place(key, (ux0 + i + 0.5) * size.x, (uy0 + j + 0.5) * size.y)


def wall_run(axis, fixed_u, plan, rot):
    """plan: [(key, u_from, u_to)] 格单元坐标; 自动按墙段长(4m)展开。
    轴向: 'x' 沿 X (墙在 y=fixed_u*4), 'y' 沿 Y (墙在 x=fixed_u*4)。
    rot: 装饰面朝向 — 'x'墙: 180=面朝+Y, 0=面朝-Y; 'y'墙: 90=面朝+X, -90=面朝-X。"""
    S = TEMPLATES["wall"][3].x
    fixed = fixed_u * S
    for key, a0, a1 in plan:
        m0, m1 = a0 * S, a1 * S
        n = max(1, round((m1 - m0) / S))
        step = (m1 - m0) / n
        for i in range(n):
            mid = m0 + (i + 0.5) * step
            if axis == "x":
                place(key, mid, fixed, rot_z=rot)
            else:
                place(key, fixed, mid, rot_z=rot)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for key, fname, d in LOADS:
        p = os.path.join(d, fname + ".glb")
        if not os.path.exists(p):
            raise FileNotFoundError(f"[{key}] {p}")
        load_template(fname, d, key=key)
    S = TEMPLATES["wall"][3].x  # 4m 模块

    # ============ A 安检大厅 (SCP, 2×2 格) ============
    floor_grid(0, 0, 2, 2)
    wall_run("x", 0, [("wall", 0, 1), ("wall_window", 1, 2)], 180)          # 南墙+观察窗
    wall_run("y", 2, [("wall_gated", 0, 1), ("wall", 1, 2)], -90)           # 东墙: 闸门+墙
    wall_run("x", 2, [("wall", 0, 2)], 0)                                  # 北墙
    wall_run("y", 0, [("wall", 0, 2)], 90)                                  # 西墙
    place("table", 2.2, 1.1, rot_z=180)
    place("chair", 2.2, 2.3, rot_z=180)
    place("cabinet", 6.9, 6.9, rot_z=180)
    place("lamp", 6.9, 1.1)
    place("candle", 4.8, 6.6)
    place("crates", 1.0, 6.9, rot_z=10)

    # ============ B0 走廊 (1×1 格) ============
    floor_grid(2, 0, 1, 1)
    wall_run("x", 0, [("wall", 2, 3)], 180)     # 南缘 y=0
    wall_run("x", 1, [("wall", 2, 3)], 0)     # 北缘 y=4

    # ============ B 后室迷宫 (4×4 格, 芥末黄) ============
    floor_grid(3, -2, 4, 4, key="carpet")
    # 西墙 x=12: 入口空开 y[0..4]
    wall_run("y", 3, [("wall_y", -2, 0), ("wall_y", 1, 2)], 90)
    # 东墙 x=28
    wall_run("y", 7, [("wall_y", -2, 2)], -90)
    # 南墙 y=-8 / 北墙 y=8 (出口空开 x[20..24])
    wall_run("x", -2, [("wall_y", 3, 7)], 180)
    wall_run("x", 2, [("wall_y", 3, 5), ("wall_y", 6, 7)], 0)
    # 内竖墙 x=20: 空开 y[-4..0] 与 y[4..8]
    wall_run("y", 5, [("wall_y", -2, -1), ("wall_y", 0, 1)], -90)
    # 内横墙 y=0: 空开 x[12..16] 与 x[20..24]
    wall_run("x", 0, [("wall_y", 3, 4), ("wall_y", 5, 6), ("wall_y", 6, 7)], 180)
    # 极度空旷: 孤独的椅子
    place("chair", 16.0, -3.0, rot_z=90)
    place("armchair", 25.0, 6.2, rot_z=-90)
    place("cabinet", 13.4, -6.9, rot_z=0)
    place("candle", 20.6, 0.6)

    # ============ C0 转换走廊 (1×1 格, 破墙) ============
    floor_grid(5, 2, 1, 1)
    wall_run("y", 5, [("wall", 2, 3)], 90)          # 西缘 x=20
    wall_run("y", 6, [("wall_broken", 2, 3)], -90)   # 东缘 x=24

    # ============ C 工业核心 (4×4 格, LC) ============
    # 地板: 跳过格栅槽位格 (i=1,2, j=1) → y[16..20] 中带
    tsize = TEMPLATES["floor"][3].x
    for i in range(4):
        for j in range(4):
            if j == 1 and i in (1, 2):
                continue
            place("floor", (3 + i + 0.5) * tsize, (3 + j + 0.5) * tsize)
    place("grate", 18.0, 18.0)                  # 下沉格栅槽 4×2
    place("grate", 22.0, 18.0)
    # 南墙 y=12: 入口空开 x[20..24]
    wall_run("x", 3, [("wall", 3, 5), ("wall", 6, 7)], 180)
    # 北墙 y=28: 中段破墙
    wall_run("x", 7, [("wall", 3, 4), ("wall_broken", 4, 5), ("wall", 5, 7)], 0)
    wall_run("y", 3, [("wall", 3, 7)], 90)          # 西墙 x=12
    wall_run("y", 7, [("wall", 3, 7)], -90)          # 东墙 x=28
    # 柱阵
    for px, py in ((14, 14), (26, 14), (14, 26), (26, 26)):
        place("pillar", px, py)
    # 钻探反应堆 (space_dark 复合件) 居中放大
    place("reactor", 20.0, 20.0, scale=2.5)
    # 警报塔 (空袭包)
    place("siren", 13.6, 13.6)
    # 战利品与杂乱
    place("crates", 13.2, 26.6, rot_z=15)
    place("crates", 26.6, 23.0, rot_z=-20)
    place("barrel", 13.1, 20.0)
    place("barrel", 26.7, 15.4)
    place("chest", 17.8, 21.6, rot_z=30)
    place("chest", 22.2, 17.6, rot_z=-15)
    place("shelf", 13.5, 24.0, rot_z=90)
    place("shelf", 26.5, 25.8, rot_z=-90)
    place("trunk", 24.2, 13.3)
    place("rubble", 24.6, 26.4, scale=0.45)
    place("rubble", 15.4, 16.0, scale=0.35)
    place("torch", 13.0, 17.4)
    place("torch", 27.0, 22.0)
    place("candle", 17.4, 24.6)
    place("candle", 23.4, 16.4)

    delete_templates()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    filtered_gltf_export(
        OUT, export_format="GLB", export_yup=True, export_apply=False,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
    )
    print("FACILITY ->", OUT)


main()
