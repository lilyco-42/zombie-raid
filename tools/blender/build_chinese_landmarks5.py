"""中式地标 · 第五批 (石作/砖石小品, 依旧避开木构飞檐):

  stone_sutra   石经幢 (须弥座+多道经带环+宝盖+宝珠, 纯石经幢)
  hitching_post 拴马桩 (石础+石柱+圆雕桩头, 驿站/道口拴马石)
  stone_pool    太液池 (圆池: 石甃池沿 + 暗水体, 园林水景)
  stone_lantern 石灯笼 (石础+石柱+发光火袋+平石板笠顶+宝珠, 平顶非飞檐)
坐标: 原点=底面中心。
运行: blender --background --python tools/blender/build_chinese_landmarks5.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def extra_materials():
    g = zh.__dict__
    # 暗水 (略带低粗糙微光, 黑童话夜池)
    g["M_POOL"] = zh.make_material("M_ZH_Pool", (0.05, 0.11, 0.13), rough=0.18, metal=0.0)
    # 灯笼暖光腔
    g["M_GLOW"] = zh.make_emissive("M_ZH_Glow", (0.95, 0.78, 0.42), 2.6)


def build_stone_sutra():
    """石经幢: 须弥座 + 经幢身 + 三道经带环 + 宝盖 + 宝珠。"""
    parts = [
        zh.cyl("SS_Base", 0.55, 0.30, (0, 0, 0.15), zh.M_STONE_D),
        zh.box("SS_Plinth", (0.78, 0.78, 0.26), (0, 0, 0.43), zh.M_STONE),
        zh.cyl("SS_Shaft", 0.27, 2.40, (0, 0, 1.70), zh.M_STONE, verts=18),
        zh.torus("SS_Ring1", 0.30, 0.06, (0, 0, 1.30), zh.M_STONE_D),
        zh.torus("SS_Ring2", 0.30, 0.06, (0, 0, 2.05), zh.M_STONE_D),
        zh.torus("SS_Ring3", 0.30, 0.06, (0, 0, 2.75), zh.M_STONE_D),
        zh.cyl("SS_Cap", 0.50, 0.20, (0, 0, 3.10), zh.M_STONE_D, verts=18),
        zh.sph("SS_Jewel", 0.17, (0, 0, 3.36), zh.M_GOLD),
    ]
    return zh.join(parts, "stone_sutra")


def build_hitching_post():
    """拴马桩: 石础 + 石柱 + 项饰环 + 圆雕桩头。"""
    parts = [
        zh.box("HP_Base", (0.52, 0.52, 0.20), (0, 0, 0.10), zh.M_STONE_D),
        zh.cyl("HP_Post", 0.16, 1.50, (0, 0, 0.95), zh.M_STONE, verts=12),
        zh.torus("HP_Collar", 0.18, 0.05, (0, 0, 1.62), zh.M_STONE_D),
        zh.sph("HP_Head", 0.21, (0, 0, 1.88), zh.M_STONE),
    ]
    return zh.join(parts, "hitching_post")


def build_stone_pool():
    """太液池: 石甃池沿 (环) + 外圈石墁 + 暗水体 (凹于沿下)。"""
    parts = [
        zh.cyl("SP_Apron", 2.70, 0.12, (0, 0, 0.0), zh.M_STONE_D, verts=40),
        zh.torus("SP_Rim", 2.45, 0.16, (0, 0, 0.10), zh.M_STONE),
        zh.cyl("SP_Water", 2.30, 0.08, (0, 0, -0.02), zh.M_POOL, verts=40),
    ]
    return zh.join(parts, "stone_pool")


def build_stone_lantern():
    """石灯笼: 石础 + 石柱 + 发光火袋 + 平石板笠顶 + 宝珠 (平顶, 非飞檐)。"""
    parts = [
        zh.cyl("SL_Base", 0.36, 0.20, (0, 0, 0.10), zh.M_STONE_D, verts=12),
        zh.cyl("SL_Pillar", 0.14, 1.00, (0, 0, 0.70), zh.M_STONE, verts=10),
        zh.box("SL_Chamber", (0.52, 0.52, 0.52), (0, 0, 1.45), zh.M_GLOW),
        zh.cyl("SL_Cap", 0.44, 0.12, (0, 0, 1.80), zh.M_STONE_D, verts=12),
        zh.sph("SL_Finial", 0.10, (0, 0, 1.92), zh.M_STONE),
    ]
    return zh.join(parts, "stone_lantern")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # import build_chinese 副作用: 重置字体缓存避免 VectorFont removed
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("stone_sutra", build_stone_sutra),
        ("hitching_post", build_hitching_post),
        ("stone_pool", build_stone_pool),
        ("stone_lantern", build_stone_lantern),
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
        print("ZHLM5 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM5_DONE")


main()
