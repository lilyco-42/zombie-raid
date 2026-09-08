"""中式地标 · 第十批 (礼制/陵墓/守水石作, 纯石, 无木构):

  stone_que      石阙 (汉阙式: 母阙+子阙+平顶石板, 成对列门; 平顶避飞檐禁区)
  stone_screen   石屏风 (观水法式三屏: 屏座+中屏+两侧屏+顶枋+边柱)
  stone_horse    石像生·石马 (神道: 座+身+颈+首+四足+尾, 陵墓仪卫)
  stone_toad     镇水兽·石蟾 (蹲伏蟾: 座+身+首+双目+四足, 守太液池)
坐标: 原点=底面中心。
运行: blender --background --python tools/blender/build_chinese_landmarks10.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def extra_materials():
    pass  # 本批纯石, 复用 M_STONE/M_STONE_D


def build_stone_que():
    """石阙 (汉阙式): 母阙 + 附子阙 + 平顶石板 (避飞檐)。"""
    parts = [
        zh.box("SQ_Base",   (1.40, 1.00, 0.40), (0.0, 0, 0.20), zh.M_STONE_D),
        zh.box("SQ_Shaft",  (1.00, 0.70, 2.60), (0.0, 0, 1.70), zh.M_STONE),
        zh.box("SQ_Cap",    (1.30, 0.90, 0.25), (0.0, 0, 3.10), zh.M_STONE),
        zh.box("SQ_ZBase",  (0.70, 0.60, 0.30), (0.9, 0, 0.15), zh.M_STONE_D),
        zh.box("SQ_ZShaft", (0.50, 0.45, 1.50), (0.9, 0, 0.95), zh.M_STONE),
        zh.box("SQ_ZCap",   (0.70, 0.70, 0.20), (0.9, 0, 1.80), zh.M_STONE_D),
    ]
    return zh.join(parts, "stone_que")


def build_stone_screen():
    """石屏风 (观水法式): 屏座 + 中屏 + 两侧屏 + 顶枋 + 边柱。"""
    parts = [
        zh.box("SS_Base",  (4.00, 0.60, 0.50), (0.0, 0, 0.25), zh.M_STONE_D),
        zh.box("SS_Mid",   (1.80, 0.25, 2.20), (0.0, 0, 1.60), zh.M_STONE),
        zh.box("SS_Left",  (1.00, 0.25, 1.80), (-1.50, 0, 1.40), zh.M_STONE),
        zh.box("SS_Right", (1.00, 0.25, 1.80), (1.50, 0, 1.40), zh.M_STONE),
        zh.box("SS_Lintel", (4.20, 0.70, 0.20), (0.0, 0, 2.80), zh.M_STONE_D),
        zh.box("SS_PostL", (0.30, 0.40, 2.40), (-2.10, 0, 1.70), zh.M_STONE_D),
        zh.box("SS_PostR", (0.30, 0.40, 2.40), (2.10, 0, 1.70), zh.M_STONE_D),
    ]
    return zh.join(parts, "stone_screen")


def build_stone_horse():
    """石像生·石马 (神道仪卫): 座 + 身 + 颈 + 首 + 四足 + 尾。"""
    parts = [
        zh.box("SH_Base", (1.80, 0.70, 0.30), (0.0, 0, 0.15), zh.M_STONE_D),
        zh.box("SH_Body", (1.40, 0.60, 0.80), (0.0, 0, 0.90), zh.M_STONE),
        zh.box("SH_Neck", (0.40, 0.40, 0.70), (0.60, 0, 1.40), zh.M_STONE),
        zh.box("SH_Head", (0.60, 0.30, 0.30), (0.95, 0, 1.70), zh.M_STONE),
        zh.box("SH_LegFL", (0.22, 0.22, 0.60), (0.50, 0.20, 0.50), zh.M_STONE_D),
        zh.box("SH_LegFR", (0.22, 0.22, 0.60), (0.50, -0.20, 0.50), zh.M_STONE_D),
        zh.box("SH_LegBL", (0.22, 0.22, 0.60), (-0.50, 0.20, 0.50), zh.M_STONE_D),
        zh.box("SH_LegBR", (0.22, 0.22, 0.60), (-0.50, -0.20, 0.50), zh.M_STONE_D),
        zh.box("SH_Tail", (0.30, 0.15, 0.40), (-0.80, 0, 1.00), zh.M_STONE),
    ]
    return zh.join(parts, "stone_horse")


def build_stone_toad():
    """镇水兽·石蟾 (蹲伏): 座 + 身 + 首 + 双目 + 四足。"""
    parts = [
        zh.box("ST_Base", (1.20, 1.00, 0.25), (0.0, 0, 0.125), zh.M_STONE_D),
        zh.sph("ST_Body", 0.55, (0.0, 0, 0.60), zh.M_STONE, seg=14, ring=8,
               scale=(1.30, 1.00, 0.70)),
        zh.box("ST_Head", (0.50, 0.45, 0.35), (0.60, 0, 0.65), zh.M_STONE),
        zh.sph("ST_EyeL", 0.09, (0.75, 0.16, 0.86), zh.M_STONE_D, seg=8, ring=6),
        zh.sph("ST_EyeR", 0.09, (0.75, -0.16, 0.86), zh.M_STONE_D, seg=8, ring=6),
        zh.box("ST_LegFL", (0.35, 0.18, 0.20), (0.35, 0.35, 0.35), zh.M_STONE),
        zh.box("ST_LegFR", (0.35, 0.18, 0.20), (0.35, -0.35, 0.35), zh.M_STONE),
        zh.box("ST_LegBL", (0.30, 0.18, 0.20), (-0.35, 0.32, 0.32), zh.M_STONE),
        zh.box("ST_LegBR", (0.30, 0.18, 0.20), (-0.35, -0.32, 0.32), zh.M_STONE),
    ]
    return zh.join(parts, "stone_toad")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("stone_que", build_stone_que),
        ("stone_screen", build_stone_screen),
        ("stone_horse", build_stone_horse),
        ("stone_toad", build_stone_toad),
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
        print("ZHLM10 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM10_DONE")


main()
