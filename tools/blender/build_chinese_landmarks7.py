"""中式地标 · 第七批 (生活级/礼制石作补充, 纯石, 无木构):

  stone_bench      石凳 (园居: 石板座 + 两石凳腿)
  stone_round_table 石圆桌 (园居: 圆桌面 + 柱 + 圆础)
  stone_basin      石盆 (叠石盆: 三层收分石圈 + 底 + 内膛, 盆景/叠水)
  stone_stele_cluster 碑林 (礼制/纪念: 共用石础 + 三碑高低错落)
坐标: 原点=底面中心。
运行: blender --background --python tools/blender/build_chinese_landmarks7.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def extra_materials():
    pass  # 本批纯石, 复用 M_STONE/M_STONE_D


def build_stone_bench():
    """石凳: 石板座 + 两石凳腿。"""
    parts = [
        zh.box("SB_Seat", (1.80, 0.50, 0.16), (0, 0, 0.55), zh.M_STONE),
        zh.box("SB_LegL", (0.22, 0.42, 0.50), (-0.75, 0, 0.25), zh.M_STONE_D),
        zh.box("SB_LegR", (0.22, 0.42, 0.50), (0.75, 0, 0.25), zh.M_STONE_D),
    ]
    return zh.join(parts, "stone_bench")


def build_stone_round_table():
    """石圆桌: 圆础 + 圆柱 + 圆桌面。"""
    parts = [
        zh.cyl("SRT_Base", 0.35, 0.15, (0, 0, 0.075), zh.M_STONE_D, verts=16),
        zh.cyl("SRT_Col", 0.18, 0.55, (0, 0, 0.40), zh.M_STONE, verts=12),
        zh.cyl("SRT_Top", 0.75, 0.12, (0, 0, 0.72), zh.M_STONE, verts=24),
    ]
    return zh.join(parts, "stone_round_table")


def build_stone_basin():
    """石盆 (叠石盆): 底 + 三层收分石圈 + 内膛。"""
    parts = [
        zh.cyl("SB_Bottom", 0.90, 0.12, (0, 0, 0.06), zh.M_STONE_D, verts=24),
        zh.cyl("SB_Ring1", 0.80, 0.18, (0, 0, 0.27), zh.M_STONE, verts=24),
        zh.cyl("SB_Ring2", 0.65, 0.18, (0, 0, 0.50), zh.M_STONE, verts=24),
        zh.cyl("SB_Ring3", 0.50, 0.16, (0, 0, 0.70), zh.M_STONE_D, verts=24),
        zh.cyl("SB_Inner", 0.42, 0.06, (0, 0, 0.66), zh.M_STONE_D, verts=20),
    ]
    return zh.join(parts, "stone_basin")


def build_stone_stele_cluster():
    """碑林: 共用石础 + 三碑高低错落 (纪念/礼制, 纯石素面)。"""
    parts = [
        zh.box("SC_Plinth", (2.40, 0.80, 0.40), (0, 0, 0.20), zh.M_STONE_D),
        zh.box("SC_S1", (0.50, 0.70, 2.00), (-0.70, 0, 1.40), zh.M_STONE),
        zh.box("SC_S2", (0.50, 0.70, 2.60), (0.00, 0, 1.70), zh.M_STONE),
        zh.box("SC_S3", (0.50, 0.70, 1.60), (0.70, 0, 1.10), zh.M_STONE),
    ]
    return zh.join(parts, "stone_stele_cluster")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("stone_bench", build_stone_bench),
        ("stone_round_table", build_stone_round_table),
        ("stone_basin", build_stone_basin),
        ("stone_stele_cluster", build_stone_stele_cluster),
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
        print("ZHLM7 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM7_DONE")


main()
