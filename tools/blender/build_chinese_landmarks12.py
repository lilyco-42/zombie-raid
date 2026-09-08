"""中式地标 · 第十二批 (桥栏 / 神道人像 / 石板平桥, 纯石, 无木构):

  bridge_balustrade   石桥栏板组 (8m: 地栿+望柱×5+柱头×5+栏板×4+抱鼓石×2)
  stone_official      石像生·文臣 (神道人像: 座+袍身+肩+首+进贤冠+笏+双袖)
  stone_general       石像生·武将 (神道人像: 座+甲身+肩+首+盔+兵杖+双臂)
  stone_slab_bridge   石板平桥 (平桥: 桥面石板+桥墩×2+桥台×2+低石栏)
坐标: 原点=底面中心。
运行: blender --background --python tools/blender/build_chinese_landmarks12.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def extra_materials():
    pass  # 本批纯石, 复用 M_STONE/M_STONE_D


def build_bridge_balustrade():
    """石桥栏板组 (8m): 地栿 + 望柱×5 + 柱头×5 + 栏板×4 + 抱鼓石×2。"""
    parts = [zh.box("BB_Sill", (8.00, 0.50, 0.25), (0, 0, 0.40), zh.M_STONE_D)]
    for i, x in enumerate((-3.60, -1.80, 0.0, 1.80, 3.60)):
        parts.append(zh.box(f"BB_Post{i}", (0.30, 0.30, 0.90), (x, 0, 0.85), zh.M_STONE))
        parts.append(zh.box(f"BB_Cap{i}", (0.36, 0.36, 0.12), (x, 0, 1.36), zh.M_STONE_D))
    for i, x in enumerate((-2.70, -0.90, 0.90, 2.70)):
        parts.append(zh.box(f"BB_Panel{i}", (1.50, 0.20, 0.55), (x, 0, 0.78), zh.M_STONE))
    for i, x in enumerate((-3.90, 3.90)):
        parts.append(zh.box(f"BB_DrumBase{i}", (0.50, 0.45, 0.60), (x, 0, 0.50), zh.M_STONE_D))
        parts.append(zh.sph(f"BB_Drum{i}", 0.26, (x, 0, 0.85), zh.M_STONE,
                            seg=12, ring=8, scale=(0.55, 0.55, 1.0)))
    return zh.join(parts, "bridge_balustrade")


def build_stone_official():
    """石像生·文臣: 冠袍持笏 (神道仪卫人像)。"""
    parts = [
        zh.box("SO_Base", (0.90, 0.70, 0.25), (0, 0, 0.125), zh.M_STONE_D),
        zh.box("SO_Robe", (0.70, 0.50, 1.30), (0, 0, 0.90), zh.M_STONE),
        zh.box("SO_Shoulder", (0.80, 0.45, 0.25), (0, 0, 1.60), zh.M_STONE),
        zh.box("SO_Head", (0.35, 0.32, 0.35), (0, 0, 1.90), zh.M_STONE),
        zh.box("SO_Hat", (0.42, 0.38, 0.18), (0, 0, 2.12), zh.M_STONE_D),
        zh.box("SO_HatTop", (0.20, 0.10, 0.15), (0, 0, 2.28), zh.M_STONE_D),
        zh.box("SO_Tablet", (0.10, 0.28, 0.50), (0, 0.18, 1.35), zh.M_STONE_D),
        zh.box("SO_SleeveL", (0.18, 0.22, 0.60), (-0.42, 0, 1.20), zh.M_STONE),
        zh.box("SO_SleeveR", (0.18, 0.22, 0.60), (0.42, 0, 1.20), zh.M_STONE),
    ]
    return zh.join(parts, "stone_official")


def build_stone_general():
    """石像生·武将: 顶盔贯甲拄兵杖 (神道仪卫人像)。"""
    parts = [
        zh.box("SGn_Base", (0.90, 0.70, 0.25), (0, 0, 0.125), zh.M_STONE_D),
        zh.box("SGn_Armor", (0.78, 0.55, 1.25), (0, 0, 0.88), zh.M_STONE),
        zh.box("SGn_Shoulder", (0.95, 0.50, 0.28), (0, 0, 1.60), zh.M_STONE),
        zh.box("SGn_Head", (0.36, 0.34, 0.35), (0, 0, 1.90), zh.M_STONE),
        zh.cone("SGn_Helm", 0.28, 0.35, (0, 0, 2.20), zh.M_STONE_D, verts=10),
        zh.sph("SGn_HelmTop", 0.09, (0, 0, 2.42), zh.M_STONE_D, seg=8, ring=6),
        zh.box("SGn_Weapon", (0.12, 0.12, 1.50), (0.42, 0, 1.00), zh.M_STONE_D),
        zh.box("SGn_Blade", (0.06, 0.14, 0.40), (0.42, 0, 1.85), zh.M_STONE),
        zh.box("SGn_ArmL", (0.20, 0.24, 0.60), (-0.50, 0, 1.20), zh.M_STONE),
        zh.box("SGn_ArmR", (0.20, 0.24, 0.60), (0.50, 0, 1.20), zh.M_STONE),
    ]
    return zh.join(parts, "stone_general")


def build_stone_slab_bridge():
    """石板平桥: 桥面石板 + 桥墩×2 + 桥台×2 + 低石栏 (区别于石拱桥)。"""
    parts = [
        zh.box("SBk_Deck", (6.00, 1.60, 0.25), (0, 0, 0.85), zh.M_STONE),
        zh.box("SBk_PierL", (0.60, 1.80, 0.70), (-1.80, 0, 0.35), zh.M_STONE_D),
        zh.box("SBk_PierR", (0.60, 1.80, 0.70), (1.80, 0, 0.35), zh.M_STONE_D),
        zh.box("SBk_AbutL", (0.60, 1.80, 0.90), (-2.90, 0, 0.45), zh.M_STONE_D),
        zh.box("SBk_AbutR", (0.60, 1.80, 0.90), (2.90, 0, 0.45), zh.M_STONE_D),
        zh.box("SBk_RailL", (6.00, 0.15, 0.35), (0, -0.72, 1.15), zh.M_STONE_D),
        zh.box("SBk_RailR", (6.00, 0.15, 0.35), (0, 0.72, 1.15), zh.M_STONE_D),
    ]
    return zh.join(parts, "stone_slab_bridge")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("bridge_balustrade", build_bridge_balustrade),
        ("stone_official", build_stone_official),
        ("stone_general", build_stone_general),
        ("stone_slab_bridge", build_stone_slab_bridge),
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
        print("ZHLM12 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM12_DONE")


main()
