"""中式地标 · 长城体系 (砖石, 模块化可拼接; 依旧避开木构飞檐)。

  greatwall_section 长城墙段模块 (8m 长 × 3.2 厚 × 6.4 高含垛口: 阶条石基 + 两段收分墙身
                    + 马道面 + 外侧垛口齿 + 内侧女儿墙; 沿 X 拼接, 与敌台/烽火台串联)
  stone_railing    石栏杆段模块 (4m: 地栿 + 望柱×3 + 栏板×2 + 素方柱头; 用于马道/池沿/墙顶)
坐标: 原点=底面中心, 外侧(垛口)朝 +Y。
运行: blender --background --python tools/blender/build_chinese_landmarks4.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def extra_materials():
    g = zh.__dict__
    g["M_BRICK"] = zh.make_material("M_ZH_Brick", (0.44, 0.40, 0.34), rough=0.95)
    g["M_BRICK_D"] = zh.make_material("M_ZH_BrickDark", (0.32, 0.29, 0.25), rough=0.95)


def build_greatwall_section():
    """长城墙段 (8m 模块): 条石基 + 收分墙身 + 马道 + 外垛口 + 内女儿墙。"""
    parts = [
        zh.box("GS_Footing", (8.4, 3.6, 0.60), (0, 0, 0.30), zh.M_BRICK_D),
        zh.box("GS_Lower", (8.0, 3.2, 2.60), (0, 0, 1.90), zh.M_BRICK),
        zh.box("GS_Upper", (7.7, 2.7, 2.20), (0, 0.1, 4.30), zh.M_BRICK),
        zh.box("GS_Walk", (8.2, 3.0, 0.18), (0, 0.05, 5.49), zh.M_BRICK_D),
        zh.box("GS_ParapetIn", (8.0, 0.35, 0.72), (0, -1.28, 5.94), zh.M_BRICK_D),
    ]
    # 外侧垛口 (每 1.4m 一齿)
    for i in range(-3, 4):
        x = i * 1.4
        parts.append(zh.box(f"GS_Crenel{i}", (0.72, 0.50, 0.92), (x, 1.32, 6.04),
                            zh.M_BRICK_D))
    return zh.join(parts, "greatwall_section")


def build_stone_railing():
    """石栏杆段 (4m 模块): 地栿 + 望柱×3 + 栏板×2 + 素方柱头 (不塑兽)。"""
    parts = [
        zh.box("SR_Sill", (4.0, 0.30, 0.14), (0, 0, 0.07), zh.M_STONE_D),
    ]
    for k, x in enumerate((-1.9, 0.0, 1.9)):
        parts.append(zh.box(f"SR_Post{k}", (0.17, 0.17, 0.95), (x, 0, 0.55), zh.M_STONE))
        parts.append(zh.box(f"SR_Cap{k}", (0.23, 0.23, 0.10), (x, 0, 1.07), zh.M_STONE_D))
    for k, x in enumerate((-0.95, 0.95)):
        parts.append(zh.box(f"SR_Panel{k}", (1.75, 0.09, 0.52), (x, 0, 0.60), zh.M_STONE))
    return zh.join(parts, "stone_railing")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # 注意: import build_chinese 会执行其模块底 main() 并缓存字体句柄,
    # 场景重置会使其失效 (VectorFont removed) → 清缓存待懒重载
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("greatwall_section", build_greatwall_section),
        ("stone_railing", build_stone_railing),
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
        print("ZHLM4 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM4_DONE")


main()
