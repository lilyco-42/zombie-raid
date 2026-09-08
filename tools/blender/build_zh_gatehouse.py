"""中式渐进式改编 Phase 1 示范: 厂区大门 + 传达室 (4m 模块组合)。

思路: 借开源资产 (KayKit 地牢/家具 收编件) 重叠裁剪整合 + 新做中式件 (chinese/) 拼装。
布局 (4m 格): 4×8m 院墙, 东格卷帘门, 西格传达室内一角 (桌/椅/搪瓷缸),
标语板贴墙, 石狮守门, 红灯笼挂门楣。
产出 assets/maps/vendor/zh_gatehouse.glb
运行: blender --background --python tools/blender/build_zh_gatehouse.py
"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_corridor import load_template, place, delete_templates, TEMPLATES
from build_vendor_lc import filtered_gltf_export, ROOT

DGN = os.path.join(ROOT, "assets", "static", "vendor", "dungeon")
CHN = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
FRN = os.path.join(ROOT, "assets", "static", "vendor", "furniture")
OUT = os.path.join(ROOT, "assets", "maps", "vendor", "zh_gatehouse.glb")

LOADS = [
    ("wall", "wall", DGN), ("pillar", "pillar", DGN),
    ("floor", "floor_tile_large", DGN),
    ("table", "table_medium", DGN), ("chair", "chair", DGN),
    ("barrel", "barrel_large", DGN), ("crates", "crates_stacked", DGN),
    ("candle", "candle_triple", DGN),
    ("door", "roller_door", CHN), ("lion", "stone_lion", CHN),
    ("lantern", "lantern_red", CHN),
    ("slogan1", "slogan_safety", CHN), ("slogan2", "slogan_tunnel", CHN),
    ("enamel", "enamel_set", CHN),
    ("cabinet", "cabinet_medium", FRN),
]


def floor_grid(ux0, uy0, nx, ny):
    size = TEMPLATES["floor"][3]
    for i in range(nx):
        for j in range(ny):
            place("floor", (ux0 + i + 0.5) * size.x, (uy0 + j + 0.5) * size.y)


def wall_run(axis, fixed_u, u0, u1, rot):
    S = TEMPLATES["wall"][3].x
    fixed = fixed_u * S
    m0, m1 = u0 * S, u1 * S
    n = max(1, round((m1 - m0) / S))
    step = (m1 - m0) / n
    for i in range(n):
        mid = m0 + (i + 0.5) * step
        if axis == "x":
            place("wall", mid, fixed, rot_z=rot)
        else:
            place("wall", fixed, mid, rot_z=rot)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for key, fname, d in LOADS:
        p = os.path.join(d, fname + ".glb")
        if not os.path.exists(p):
            raise FileNotFoundError(f"[{key}] {p}")
        load_template(fname, d, key=key)

    # ---- 地面 x[0..8] y[-4..4] ----
    floor_grid(0, -1, 2, 2)
    # ---- 围墙: 后墙/东西墙/前墙(西格墙+东格卷帘门) ----
    wall_run("x", 1, 0, 2, 180)      # 北墙 y=4 (面朝院内 -Y)
    wall_run("y", 0, -1, 1, 90)      # 西墙 x=0 (面朝院内 +X)
    wall_run("y", 2, -1, 1, -90)     # 东墙 x=8 (面朝院内 -X)
    wall_run("x", -1, 0, 1, 0)       # 南墙西段 y=-4
    place("door", 6.0, -4.0, rot_z=0)  # 南墙东格 = 卷帘门 (4m 模块)
    # ---- 四角柱 ----
    for px, py in ((0.75, 3.25), (7.25, 3.25), (0.75, -3.25)):
        place("pillar", px, py)
    # ---- 门卫/传达室一角 (西北) ----
    place("table", 1.7, 2.6, rot_z=180)
    place("chair", 1.7, 1.4, rot_z=0)
    place("enamel", 1.35, 2.5, z=0.82)          # 桌面 (渲染后校正)
    place("cabinet", 3.4, 3.3, rot_z=180)
    place("candle", 2.1, 2.7, z=0.82)
    # ---- 标语板: 西墙内侧(字面朝 +X) + 北墙内侧(字面朝 -Y 朝院内) ----
    place("slogan1", 1.0, 0.4, rot_z=90)        # 安全生产 人人有责
    place("slogan2", 4.2, 3.2, rot_z=0)         # 深挖洞 广积粮
    # ---- 门口阵势 ----
    place("lion", 4.3, -6.3, rot_z=0)           # 石狮朝门外 (-Y)
    place("lion", 7.7, -6.3, rot_z=0)
    place("lantern", 4.7, -4.45, z=2.7)         # 灯笼挂门外墙面
    place("lantern", 7.3, -4.45, z=2.7)
    # ---- 杂物 ----
    place("barrel", 7.1, 2.8)
    place("crates", 0.95, -2.9, rot_z=12)

    delete_templates()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    filtered_gltf_export(
        OUT, export_format="GLB", export_yup=True, export_apply=False,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
    )
    print("ZH_GATEHOUSE ->", OUT)


main()
