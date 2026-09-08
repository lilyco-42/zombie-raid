"""中式地标 · 第十一批 (神道石像生补全 / 碑廊 / 石五供, 纯石, 无木构):

  stone_sheep         石像生·石羊 (神道: 座+蜷身+首+双角+四足+尾)
  stone_tiger         石像生·石虎 (神道: 座+蹲身+胸+首+双耳+四足+长尾)
  stele_gallery       碑廊 (低石墙 + 四碑 + 平顶廊板 + 端柱; 区别碑林/单碑)
  stone_five_offering 石五供 (石祭台: 中香炉 + 双烛台 + 双花瓶)
坐标: 原点=底面中心。
运行: blender --background --python tools/blender/build_chinese_landmarks11.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def extra_materials():
    pass  # 本批纯石, 复用 M_STONE/M_STONE_D


def build_stone_sheep():
    """石像生·石羊: 蜷卧羊 (神道仪卫, 与石马配对)。"""
    parts = [
        zh.box("SSp_Base", (1.30, 0.70, 0.25), (0.0, 0, 0.125), zh.M_STONE_D),
        zh.box("SSp_Body", (1.00, 0.55, 0.60), (0.0, 0, 0.65), zh.M_STONE),
        zh.box("SSp_Head", (0.40, 0.35, 0.35), (0.60, 0, 0.85), zh.M_STONE),
        zh.sph("SSp_HornL", 0.09, (0.78, 0.16, 1.03), zh.M_STONE_D, seg=8, ring=6),
        zh.sph("SSp_HornR", 0.09, (0.78, -0.16, 1.03), zh.M_STONE_D, seg=8, ring=6),
        zh.box("SSp_LegFL", (0.18, 0.18, 0.35), (0.35, 0.20, 0.30), zh.M_STONE_D),
        zh.box("SSp_LegFR", (0.18, 0.18, 0.35), (0.35, -0.20, 0.30), zh.M_STONE_D),
        zh.box("SSp_LegBL", (0.18, 0.18, 0.35), (-0.35, 0.20, 0.30), zh.M_STONE_D),
        zh.box("SSp_LegBR", (0.18, 0.18, 0.35), (-0.35, -0.20, 0.30), zh.M_STONE_D),
        zh.box("SSp_Tail", (0.25, 0.12, 0.12), (-0.60, 0, 0.75), zh.M_STONE),
    ]
    return zh.join(parts, "stone_sheep")


def build_stone_tiger():
    """石像生·石虎: 蹲踞虎 (神道仪卫, 与石马/石羊同列)。"""
    parts = [
        zh.box("STg_Base", (1.40, 0.80, 0.25), (0.0, 0, 0.125), zh.M_STONE_D),
        zh.box("STg_Body", (1.10, 0.60, 0.65), (0.0, 0, 0.70), zh.M_STONE),
        zh.box("STg_Chest", (0.50, 0.50, 0.50), (0.55, 0, 0.95), zh.M_STONE),
        zh.box("STg_Head", (0.50, 0.45, 0.45), (0.80, 0, 1.15), zh.M_STONE),
        zh.cone("STg_EarL", 0.09, 0.15, (0.75, 0.18, 1.45), zh.M_STONE_D, verts=8),
        zh.cone("STg_EarR", 0.09, 0.15, (0.75, -0.18, 1.45), zh.M_STONE_D, verts=8),
        zh.box("STg_LegFL", (0.20, 0.20, 0.40), (0.40, 0.25, 0.35), zh.M_STONE_D),
        zh.box("STg_LegFR", (0.20, 0.20, 0.40), (0.40, -0.25, 0.35), zh.M_STONE_D),
        zh.box("STg_LegBL", (0.20, 0.20, 0.40), (-0.40, 0.25, 0.35), zh.M_STONE_D),
        zh.box("STg_LegBR", (0.20, 0.20, 0.40), (-0.40, -0.25, 0.35), zh.M_STONE_D),
        zh.box("STg_Tail", (0.50, 0.14, 0.14), (-0.70, 0, 0.85), zh.M_STONE),
    ]
    return zh.join(parts, "stone_tiger")


def build_stele_gallery():
    """碑廊: 低石墙 + 四碑 + 平顶廊板 + 端柱 (平顶避飞檐)。"""
    parts = [
        zh.box("SG_Wall", (6.00, 0.70, 0.90), (0.0, 0, 0.45), zh.M_STONE_D),
        zh.box("SG_S1", (0.55, 0.30, 1.70), (-2.10, 0, 1.55), zh.M_STONE),
        zh.box("SG_S2", (0.55, 0.30, 1.70), (-0.70, 0, 1.55), zh.M_STONE),
        zh.box("SG_S3", (0.55, 0.30, 1.70), (0.70, 0, 1.55), zh.M_STONE),
        zh.box("SG_S4", (0.55, 0.30, 1.70), (2.10, 0, 1.55), zh.M_STONE),
        zh.box("SG_Slab", (6.40, 1.00, 0.25), (0.0, 0, 2.52), zh.M_STONE),
        zh.box("SG_PostL", (0.40, 0.60, 2.40), (-3.20, 0, 1.40), zh.M_STONE_D),
        zh.box("SG_PostR", (0.40, 0.60, 2.40), (3.20, 0, 1.40), zh.M_STONE_D),
    ]
    return zh.join(parts, "stele_gallery")


def build_stone_five_offering():
    """石五供: 石祭台上中香炉 + 双烛台 + 双花瓶 (陵墓祭祀)。"""
    parts = [zh.box("SF_Base", (3.00, 0.70, 0.25), (0.0, 0, 0.125), zh.M_STONE_D)]
    # 中: 香炉 (座 + 上敛炉身 + 口沿)
    parts += [
        zh.cyl("SF_CFoot", 0.22, 0.10, (0, 0, 0.30), zh.M_STONE_D, verts=14),
        zh.cone("SF_CBody", 0.28, 0.34, (0, 0, 0.52), zh.M_STONE, verts=14, r_top=0.20),
        zh.torus("SF_CRim", 0.20, 0.04, (0, 0, 0.70), zh.M_STONE_D, rot=(0, 0, 0)),
    ]
    # 次: 双烛台 (座 + 柱 + 承盘)
    for i, x in enumerate((-0.60, 0.60)):
        parts += [
            zh.cyl(f"SF_Cd{i}Base", 0.16, 0.10, (x, 0, 0.30), zh.M_STONE_D, verts=12),
            zh.cyl(f"SF_Cd{i}Stem", 0.055, 0.42, (x, 0, 0.56), zh.M_STONE, verts=10),
            zh.cyl(f"SF_Cd{i}Cup", 0.12, 0.08, (x, 0, 0.81), zh.M_STONE_D, verts=12),
        ]
    # 外: 双花瓶 (座 + 瓶身 + 瓶颈)
    for i, x in enumerate((-1.20, 1.20)):
        parts += [
            zh.cyl(f"SF_V{i}Base", 0.15, 0.09, (x, 0, 0.295), zh.M_STONE_D, verts=12),
            zh.cone(f"SF_V{i}Body", 0.19, 0.44, (x, 0, 0.55), zh.M_STONE, verts=12,
                    r_top=0.11),
            zh.cyl(f"SF_V{i}Neck", 0.075, 0.12, (x, 0, 0.83), zh.M_STONE_D, verts=10),
        ]
    return zh.join(parts, "stone_five_offering")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("stone_sheep", build_stone_sheep),
        ("stone_tiger", build_stone_tiger),
        ("stele_gallery", build_stele_gallery),
        ("stone_five_offering", build_stone_five_offering),
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
        print("ZHLM11 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM11_DONE")


main()
