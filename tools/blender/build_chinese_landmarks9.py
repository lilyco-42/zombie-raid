"""中式地标 · 第九批 (园居/礼制石作补充, 纯石, 无木构):

  stone_hex_pavilion  六角石亭 (平顶六边石板, 六柱+平顶+础台; 避飞檐禁区)
  sutra_cluster       石经幢群 (三经幢高矮错落共一础, 区别单件 stone_sutra/碑林)
  stone_water_beast   镇水兽·石犀 (纯石素面, 守太液池/奈何桥)
  lion_post           望柱石狮 (石柱顶小石狮, 成对守园门; 区别 stone_lion/wangzhu)
坐标: 原点=底面中心。
运行: blender --background --python tools/blender/build_chinese_landmarks9.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def extra_materials():
    pass  # 本批纯石, 复用 M_STONE/M_STONE_D


def build_stone_hex_pavilion():
    """六角石亭: 平顶六边石板 (避飞檐), 六石柱 + 平顶 + 础台。"""
    parts = [zh.cyl("HP_Base", 2.00, 0.30, (0, 0, 0.15), zh.M_STONE_D, verts=6)]
    for i, (dx, dy) in enumerate([
            (1.60, 0.00), (0.80, 1.39), (-0.80, 1.39),
            (-1.60, 0.00), (-0.80, -1.39), (0.80, -1.39)]):
        parts.append(zh.cyl(f"HP_Col{i}", 0.16, 2.00, (dx, dy, 1.30),
                            zh.M_STONE, verts=8))
    parts.append(zh.cyl("HP_Roof", 2.30, 0.25, (0, 0, 2.42), zh.M_STONE, verts=6))
    parts.append(zh.cyl("HP_Cap", 1.60, 0.16, (0, 0, 2.63), zh.M_STONE_D, verts=6))
    return zh.join(parts, "stone_hex_pavilion")


def build_sutra_cluster():
    """石经幢群: 三经幢高矮错落共一础, 纯石素面。"""
    parts = [zh.box("SC2_Base", (2.40, 1.40, 0.40), (0, 0, 0.20), zh.M_STONE_D)]
    plinth_h, base_top = 0.30, 0.55
    for i, (x, sh) in enumerate([(-0.80, 1.80), (0.0, 2.20), (0.80, 1.60)]):
        parts.append(zh.box(f"SC2_P{i}", (0.40, 0.40, plinth_h),
                            (x, 0, base_top), zh.M_STONE))
        parts.append(zh.box(f"SC2_S{i}", (0.30, 0.30, sh),
                            (x, 0, base_top + plinth_h / 2 + sh / 2), zh.M_STONE))
        cap_y = base_top + plinth_h / 2 + sh + 0.05
        parts.append(zh.torus(f"SC2_C{i}", 0.22, 0.05, (x, 0, cap_y), zh.M_STONE_D))
        parts.append(zh.sph(f"SC2_Prl{i}", 0.12, (x, 0, cap_y + 0.12),
                           zh.M_STONE, seg=10, ring=6))
    return zh.join(parts, "sutra_cluster")


def build_stone_water_beast():
    """镇水兽·石犀: 纯石素面, 守太液池/奈何桥。"""
    parts = [
        zh.box("WB_Body", (1.80, 0.90, 0.80), (0, 0, 0.70), zh.M_STONE_D),
        zh.box("WB_Head", (0.60, 0.60, 0.60), (1.00, 0, 0.95), zh.M_STONE),
        zh.box("WB_Snout", (0.40, 0.40, 0.30), (1.40, 0, 0.80), zh.M_STONE),
        zh.box("WB_LegFL", (0.30, 0.30, 0.50), (0.60, 0.35, 0.25), zh.M_STONE),
        zh.box("WB_LegFR", (0.30, 0.30, 0.50), (0.60, -0.35, 0.25), zh.M_STONE),
        zh.box("WB_LegBL", (0.30, 0.30, 0.50), (-0.60, 0.35, 0.25), zh.M_STONE),
        zh.box("WB_LegBR", (0.30, 0.30, 0.50), (-0.60, -0.35, 0.25), zh.M_STONE),
        zh.cone("WB_Horn", 0.08, 0.30, (1.20, 0, 1.35), zh.M_STONE_D, verts=8),
        zh.box("WB_Tail", (0.50, 0.15, 0.15), (-1.00, 0, 0.90), zh.M_STONE),
    ]
    return zh.join(parts, "stone_water_beast")


def build_lion_post():
    """望柱石狮: 石柱顶小石狮(坐式), 成对守园门。"""
    parts = [
        zh.box("LP_Base", (0.50, 0.50, 0.30), (0, 0, 0.15), zh.M_STONE_D),
        zh.cyl("LP_Shaft", 0.18, 1.40, (0, 0, 0.95), zh.M_STONE, verts=12),
        zh.box("LP_LBody", (0.40, 0.50, 0.40), (0, 0, 1.90), zh.M_STONE),
        zh.box("LP_LHead", (0.30, 0.30, 0.28), (0, -0.25, 2.10), zh.M_STONE),
        zh.box("LP_LPawL", (0.12, 0.18, 0.10), (-0.12, -0.28, 1.80), zh.M_STONE_D),
        zh.box("LP_LPawR", (0.12, 0.18, 0.10), (0.12, -0.28, 1.80), zh.M_STONE_D),
    ]
    return zh.join(parts, "lion_post")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("stone_hex_pavilion", build_stone_hex_pavilion),
        ("sutra_cluster", build_sutra_cluster),
        ("stone_water_beast", build_stone_water_beast),
        ("lion_post", build_lion_post),
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
        print("ZHLM9 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM9_DONE")


main()
