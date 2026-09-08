"""中式地标 · 第六批 (生活级石作: 园扉/踏跺/磨盘/石槽, 纯石, 无木构):

  stone_arch   石坊 (无顶石牌坊, 坊柱+石础+上下额枋, 纯石素面, 与冲天柱式 paifang 区分)
  stone_stair  石阶 (踏跺, 4 级, 园/台基入口)
  stone_mill   石磨 (磨盘: 静盘+动盘+磨柄+料斗, 生活级农作器物)
  stone_trough 石槽 (敞口石水槽, U 形: 底板+长侧+端板, 厩/园汲水)
坐标: 原点=底面中心。
运行: blender --background --python tools/blender/build_chinese_landmarks6.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def extra_materials():
    # 本批纯石, 复用 M_STONE/M_STONE_D 即可, 无需新增材质
    pass


def build_stone_arch():
    """石坊 (无顶石牌坊): 双坊柱 + 石础 + 上下额枋, 素面纯石。"""
    parts = [
        zh.box("SA_BaseL", (0.82, 0.82, 0.42), (-2.2, 0, 0.21), zh.M_STONE_D),
        zh.box("SA_BaseR", (0.82, 0.82, 0.42), (2.2, 0, 0.21), zh.M_STONE_D),
        zh.box("SA_PillarL", (0.60, 0.60, 4.20), (-2.2, 0, 2.31), zh.M_STONE),
        zh.box("SA_PillarR", (0.60, 0.60, 4.20), (2.2, 0, 2.31), zh.M_STONE),
        zh.box("SA_Lintel1", (5.60, 0.70, 0.52), (0, 0, 3.45), zh.M_STONE_D),
        zh.box("SA_Lintel2", (6.00, 0.92, 0.42), (0, 0, 4.02), zh.M_STONE),
    ]
    return zh.join(parts, "stone_arch")


def build_stone_stair():
    """石阶 (踏跺): 4 级, 沿 +Y 递进上升。"""
    parts = []
    for i in range(4):
        parts.append(zh.box(f"SS_Step{i}", (3.0, 0.5, 0.30),
                             (0, -0.75 + i * 0.5, 0.15 + i * 0.30), zh.M_STONE_D))
    return zh.join(parts, "stone_stair")


def build_stone_mill():
    """石磨: 石础 + 静盘 + 动盘 + 磨柄 + 料斗 (生活级农作器物)。"""
    parts = [
        zh.box("SM_Base", (1.40, 1.40, 0.50), (0, 0, 0.25), zh.M_STONE_D),
        zh.cyl("SM_Lower", 0.90, 0.25, (0, 0, 0.625), zh.M_STONE, verts=24),
        zh.cyl("SM_Upper", 0.85, 0.25, (0, 0, 0.875), zh.M_STONE, verts=24),
        zh.box("SM_Handle", (0.55, 0.12, 0.12), (0.55, 0, 0.95), zh.M_STONE_D),
        zh.box("SM_Hopper", (0.40, 0.40, 0.42), (0, 0, 1.20), zh.M_STONE),
    ]
    return zh.join(parts, "stone_mill")


def build_stone_trough():
    """石槽: 敞口 U 形 (底板 + 两长侧 + 两端板)。"""
    parts = [
        zh.box("ST_Bottom", (2.40, 1.00, 0.20), (0, 0, 0.10), zh.M_STONE_D),
        zh.box("ST_SideA", (2.40, 0.15, 0.42), (0, 0.42, 0.31), zh.M_STONE),
        zh.box("ST_SideB", (2.40, 0.15, 0.42), (0, -0.42, 0.31), zh.M_STONE),
        zh.box("ST_EndA", (0.15, 0.70, 0.42), (-1.12, 0, 0.31), zh.M_STONE),
        zh.box("ST_EndB", (0.15, 0.70, 0.42), (1.12, 0, 0.31), zh.M_STONE),
    ]
    return zh.join(parts, "stone_trough")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("stone_arch", build_stone_arch),
        ("stone_stair", build_stone_stair),
        ("stone_mill", build_stone_mill),
        ("stone_trough", build_stone_trough),
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
        print("ZHLM6 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM6_DONE")


main()
