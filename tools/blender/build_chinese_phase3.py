"""中式渐进式改编 Phase 3: 礼制/生活构件 6 件 (依 docs/chinese_architecture_survey.md §4 自建分界)。

  paifang 牌坊 (冲天柱式: 避开飞檐, 两柱一间 + 额枋花板 + 「永昌」金匾 + 嵌柱楹联)
  mendun 门墩抱鼓石 (单件, 成对放置) / bronze_bell 铜钟钟架 (摇警报三下事件锚点)
  well 井台辘轳 / offering_table 供桌 / paper_ash 纸钱灰堆
运行: blender --background --python tools/blender/build_chinese_phase3.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PI = math.pi


def extra_materials():
    g = zh.__dict__
    g["M_BRONZE"] = zh.make_material("M_ZH_Bronze", (0.34, 0.27, 0.17), rough=0.45, metal=0.7)
    g["M_LACQ"] = zh.make_material("M_ZH_Lacquer", (0.22, 0.12, 0.08), rough=0.5)
    g["M_ASH"] = zh.make_material("M_ZH_Ash", (0.09, 0.09, 0.088), rough=0.95)
    g["M_PAPER"] = zh.make_material("M_ZH_Paper", (0.82, 0.80, 0.74), rough=0.9)
    g["M_GOLD"] = g.get("M_GOLD") or zh.make_material("M_ZH_Gold", (0.80, 0.64, 0.20), rough=0.35, metal=0.8)
    g["M_JAR"] = zh.make_material("M_ZH_Jar", (0.13, 0.12, 0.115), rough=0.8)
    g["M_WATER"] = zh.make_material("M_ZH_Water", (0.05, 0.07, 0.08), rough=0.15)


def build_paifang():
    """冲天柱式牌坊 (无顶, 避开飞檐): 双柱 + 双额枋 + 花板金匾 + 嵌柱楹联 + 云罐柱头。"""
    parts = []
    for sx, tag in ((-1.5, "L"), (1.5, "R")):
        parts += [
            zh.box(f"PF_Foot{tag}", (0.52, 0.52, 0.26), (sx, 0, 0.13), zh.M_STONE_D),
            zh.cyl(f"PF_Col{tag}", 0.17, 3.9, (sx, 0, 1.95), zh.M_STONE, verts=14),
            zh.cyl(f"PF_Crown{tag}", 0.13, 0.28, (sx, 0, 4.05), zh.M_STONE_D, verts=10),
            zh.sph(f"PF_Knob{tag}", 0.11, (sx, 0, 4.26), zh.M_GOLD, seg=10, ring=6),
        ]
    parts += [
        zh.box("PF_BeamHi", (3.9, 0.28, 0.32), (0, 0, 3.30), zh.M_STONE_D),
        zh.box("PF_Board", (3.2, 0.12, 0.55), (0, 0, 2.85), zh.M_STONE),
        zh.box("PF_BeamLo", (3.8, 0.22, 0.22), (0, 0, 2.42), zh.M_STONE_D),
    ]
    # 金匾: 深漆板 + 「永昌」金字
    parts.append(zh.box("PF_Plaque", (1.15, 0.07, 0.42), (0, -0.10, 2.86), zh.M_LACQ))
    t = zh.text_mesh("永昌", zh.M_GOLD, 0.26, (0, -0.16, 2.86), rot=(PI / 2, 0, 0), extrude=0.015)
    if t is not None:
        parts.append(t)
    # 嵌柱楹联: 竖板逐字堆叠 (右: 雾锁千秋骨 / 左: 灯照野魂归 — 上下联)
    couplets = {
        1.16: ["灯", "照", "野", "魂", "归"],
        -1.16: ["雾", "锁", "千", "秋", "骨"],
    }
    for cx, chars in couplets.items():
        parts.append(zh.box(f"PF_Couplet{cx}", (0.20, 0.05, 1.95), (cx, -0.20, 1.35), zh.M_LACQ))
        for i, ch in enumerate(chars):
            zc = 2.12 - i * 0.40
            tc = zh.text_mesh(ch, zh.M_GOLD, 0.21, (cx, -0.24, zc), rot=(PI / 2, 0, 0), extrude=0.012)
            if tc is not None:
                parts.append(tc)
    return zh.join(parts, "paifang")


def build_mendun():
    """门墩抱鼓石 (单件): 基座 + 书箱体 + 抱鼓。装饰面朝 -Y。"""
    parts = [
        zh.box("MD_Base", (0.46, 0.82, 0.26), (0, 0, 0.13), zh.M_STONE_D),
        zh.box("MD_Chest", (0.38, 0.44, 0.34), (0, -0.16, 0.43), zh.M_STONE),
        zh.cyl("MD_Drum", 0.27, 0.13, (0, 0.16, 0.56), zh.M_STONE, verts=20, rot=(PI / 2, 0, 0)),
        zh.torus("MD_DrumRim", 0.26, 0.018, (0, 0.22, 0.56), zh.M_STONE_D),
    ]
    return zh.join(parts, "mendun")


def build_bronze_bell():
    """铜钟钟架: 双柱横梁 + 悬钟 + 钟钮 + 撞木 (摇/撞三下 = 事件锚点)。"""
    parts = [
        zh.box("BB_PostL", (0.13, 0.13, 2.7), (-0.95, 0, 1.35), zh.M_LACQ),
        zh.box("BB_PostR", (0.13, 0.13, 2.7), (0.95, 0, 1.35), zh.M_LACQ),
        zh.box("BB_Beam", (2.3, 0.17, 0.17), (0, 0, 2.62), zh.M_LACQ),
        zh.box("BB_BaseL", (0.4, 0.4, 0.1), (-0.95, 0, 0.05), zh.M_STONE_D),
        zh.box("BB_BaseR", (0.4, 0.4, 0.1), (0.95, 0, 0.05), zh.M_STONE_D),
        zh.torus("BB_Hook", 0.06, 0.015, (0, 0, 2.44), zh.M_BRONZE),
        zh.cone("BB_Bell", 0.44, 0.72, (0, 0, 2.02), zh.M_BRONZE, verts=20, r_top=0.30),
        zh.torus("BB_BellLip", 0.435, 0.025, (0, 0, 1.68), zh.M_BRONZE),
        zh.cyl("BB_Striker", 0.045, 0.55, (0.30, 0, 1.55), zh.M_LACQ, rot=(0, 0.35, 0)),
    ]
    return zh.join(parts, "bronze_bell")


def build_well():
    """井台辘轳: 石台 + 井圈 + 双柱轴架 + 摇柄 + 吊桶。"""
    parts = [
        zh.box("WE_Platform", (1.7, 1.7, 0.14), (0, 0, 0.07), zh.M_STONE_D),
        zh.cyl("WE_Curb", 0.56, 0.5, (0, 0, 0.39), zh.M_STONE, verts=20),
        zh.cyl("WE_Hole", 0.42, 0.12, (0, 0, 0.60), zh.M_JAR if "M_JAR" in zh.__dict__ else zh.M_STONE_D,
               verts=20),
        zh.cyl("WE_Water", 0.40, 0.03, (0, 0, 0.28), zh.M_WATER if "M_WATER" in zh.__dict__ else zh.M_STONE_D,
               verts=18),
        zh.box("WE_PostL", (0.09, 0.09, 1.5), (-0.62, 0, 0.89), zh.M_LACQ),
        zh.box("WE_PostR", (0.09, 0.09, 1.5), (0.62, 0, 0.89), zh.M_LACQ),
        zh.cyl("WE_Axle", 0.05, 1.5, (0, 0, 1.58), zh.M_LACQ, verts=10, rot=(0, PI / 2, 0)),
        zh.cyl("WE_Crank", 0.03, 0.30, (0.80, 0.20, 1.58), zh.M_LACQ, verts=8, rot=(PI / 2, 0, 0)),
        zh.cyl("WE_Rope", 0.013, 0.75, (0, 0, 1.15), zh.M_PAPER, verts=6),
        zh.cyl("WE_Bucket", 0.11, 0.16, (0, 0, 0.70), zh.M_LACQ, verts=10),
    ]
    return zh.join(parts, "well")


def build_offering_table():
    """供桌: 高脚窄桌 (桌高 0.98), 案面外挑。"""
    parts = [zh.box("OT_Top", (1.34, 0.52, 0.06), (0, 0, 0.95), zh.M_LACQ)]
    for sx in (-0.56, 0.56):
        for sy in (-0.19, 0.19):
            parts.append(zh.box(f"OT_Leg{sx}{sy}", (0.06, 0.06, 0.92), (sx, sy, 0.46), zh.M_LACQ))
    parts += [
        zh.box("OT_ApronN", (1.24, 0.04, 0.16), (0, 0.19, 0.82), zh.M_LACQ),
        zh.box("OT_ApronS", (1.24, 0.04, 0.16), (0, -0.19, 0.82), zh.M_LACQ),
        zh.box("OT_Drawer", (0.5, 0.04, 0.16), (0, -0.21, 0.60), zh.M_LACQ),
    ]
    return zh.join(parts, "offering_table")


def build_paper_ash():
    """纸钱灰堆: 灰丘 + 散落纸片 + 余香杆。"""
    parts = [
        zh.cone("PA_Mound", 0.48, 0.16, (0, 0, 0.08), zh.M_ASH, verts=14),
        zh.box("PA_P1", (0.16, 0.11, 0.006), (0.22, 0.14, 0.13), zh.M_PAPER, rot=(0.3, 0.2, 0.5)),
        zh.box("PA_P2", (0.14, 0.10, 0.006), (-0.18, 0.10, 0.12), zh.M_PAPER, rot=(0.25, -0.15, 1.2)),
        zh.box("PA_P3", (0.15, 0.12, 0.006), (0.05, -0.20, 0.12), zh.M_PAPER, rot=(-0.2, 0.3, 2.1)),
        zh.cyl("PA_Stick1", 0.008, 0.30, (-0.06, 0.02, 0.22), zh.M_LACQ, verts=6, rot=(0.12, 0.08, 0)),
        zh.cyl("PA_Stick2", 0.008, 0.28, (0.05, -0.04, 0.21), zh.M_LACQ, verts=6, rot=(-0.1, 0.1, 0)),
    ]
    return zh.join(parts, "paper_ash")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # 注意: import build_chinese 会执行其模块底 main() 并缓存字体句柄,
    # 场景重置会使其失效 (VectorFont removed) → 清缓存待懒重载
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("paifang", build_paifang),
        ("mendun", build_mendun),
        ("bronze_bell", build_bronze_bell),
        ("well", build_well),
        ("offering_table", build_offering_table),
        ("paper_ash", build_paper_ash),
    ]
    for name, fn in builders:
        zh.refresh_materials()
        extra_materials()
        zh.delete_all()
        obj = fn()
        path = os.path.join(OUT, name + ".glb")
        filtered_gltf_export(
            path, export_format="GLB", export_yup=True, export_apply=False,
            export_materials="EXPORT", export_cameras=False, export_lights=False,
        )
        print("ZH3 ->", path, "verts=", len(obj.data.vertices))
    print("ZH3_DONE")


main()
