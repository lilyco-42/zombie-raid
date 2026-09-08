"""中式地标 · 第八批 (园居/礼制石作补充, 纯石, 无木构):

  stone_pavilion  无顶石亭 (平顶石板, 四石柱+平顶+础台; 避飞檐禁区, 平顶石板可期)
  wangzhu         望柱 (云纹石柱, 几何雕刻顶非石狮, 用于桥/坛/径列柱)
  stone_bixi      石赑屃碑座 (龟驮碑, 纯石素面, 配碑林)
  stone_censer    石鼎香炉 (三足石鼎, 区别于青铜 incense_burner)
坐标: 原点=底面中心。
运行: blender --background --python tools/blender/build_chinese_landmarks8.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def extra_materials():
    pass  # 本批纯石, 复用 M_STONE/M_STONE_D


def build_stone_pavilion():
    """无顶石亭: 平顶石板 (避木构飞檐), 四石柱 + 平顶 + 础台。"""
    parts = [
        zh.box("SP_Base", (3.60, 3.60, 0.30), (0, 0, 0.15), zh.M_STONE_D),
        zh.cyl("SP_ColFL", 0.18, 2.10, (-1.50, -1.50, 1.35), zh.M_STONE, verts=12),
        zh.cyl("SP_ColFR", 0.18, 2.10, ( 1.50, -1.50, 1.35), zh.M_STONE, verts=12),
        zh.cyl("SP_ColBL", 0.18, 2.10, (-1.50,  1.50, 1.35), zh.M_STONE, verts=12),
        zh.cyl("SP_ColBR", 0.18, 2.10, ( 1.50,  1.50, 1.35), zh.M_STONE, verts=12),
        zh.box("SP_Roof", (4.20, 4.20, 0.30), (0, 0, 2.55), zh.M_STONE),
        zh.box("SP_Cap",  (3.40, 3.40, 0.16), (0, 0, 2.78), zh.M_STONE_D),
    ]
    return zh.join(parts, "stone_pavilion")


def build_wangzhu():
    """望柱: 云纹石柱 (几何雕刻顶, 非石狮), 用于桥/坛/径列柱。"""
    parts = [
        zh.box("WZ_Base", (0.50, 0.50, 0.30), (0, 0, 0.15), zh.M_STONE_D),
        zh.cyl("WZ_Shaft", 0.18, 1.60, (0, 0, 1.10), zh.M_STONE, verts=12),
        zh.torus("WZ_Ring", 0.20, 0.05, (0, 0, 1.78), zh.M_STONE_D, rot=(0, 0, 0)),
        zh.sph("WZ_Knob", 0.20, (0, 0, 2.02), zh.M_STONE, seg=12, ring=8),
    ]
    return zh.join(parts, "wangzhu")


def build_stone_bixi():
    """石赑屃碑座 (龟驮碑): 纯石素面, 配碑林。"""
    parts = [
        zh.box("BX_Body",  (2.20, 1.40, 0.50), (0, 0, 0.25), zh.M_STONE_D),
        zh.box("BX_Head",  (0.55, 0.55, 0.42), (1.25, 0, 0.42), zh.M_STONE),
        zh.box("BX_LegFL", (0.45, 0.45, 0.30), (-0.80,  0.55, 0.15), zh.M_STONE),
        zh.box("BX_LegFR", (0.45, 0.45, 0.30), (-0.80, -0.55, 0.15), zh.M_STONE),
        zh.box("BX_LegBL", (0.45, 0.45, 0.30), ( 0.80,  0.55, 0.15), zh.M_STONE_D),
        zh.box("BX_LegBR", (0.45, 0.45, 0.30), ( 0.80, -0.55, 0.15), zh.M_STONE_D),
        zh.sph("BX_Shell", 0.95, (0, 0, 0.62), zh.M_STONE, seg=16, ring=10,
               scale=(1.25, 1.0, 0.62)),
        zh.box("BX_Stele", (0.70, 0.25, 1.80), (0, 0, 1.45), zh.M_STONE),
    ]
    return zh.join(parts, "stone_bixi")


def build_stone_censer():
    """石鼎香炉 (三足石鼎), 区别于青铜 incense_burner。"""
    parts = [
        zh.cyl("SC_Foot", 0.52, 0.12, (0, 0, 0.06), zh.M_STONE_D, verts=16),
        zh.cone("SC_Bowl", 0.46, 0.55, (0, 0, 0.42), zh.M_STONE, verts=16, r_top=0.30),
        zh.torus("SC_Rim", 0.30, 0.05, (0, 0, 0.70), zh.M_STONE_D, rot=(math.pi / 2, 0, 0)),
        zh.cyl("SC_Leg1", 0.07, 0.40, ( 0.00,  0.33, 0.20), zh.M_STONE_D, verts=8),
        zh.cyl("SC_Leg2", 0.07, 0.40, (-0.29, -0.17, 0.20), zh.M_STONE_D, verts=8),
        zh.cyl("SC_Leg3", 0.07, 0.40, ( 0.29, -0.17, 0.20), zh.M_STONE_D, verts=8),
        zh.torus("SC_HandL", 0.11, 0.03, ( 0.46, 0, 0.55), zh.M_STONE, rot=(math.pi / 2, 0, 0)),
        zh.torus("SC_HandR", 0.11, 0.03, (-0.46, 0, 0.55), zh.M_STONE, rot=(math.pi / 2, 0, 0)),
    ]
    return zh.join(parts, "stone_censer")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("stone_pavilion", build_stone_pavilion),
        ("wangzhu", build_wangzhu),
        ("stone_bixi", build_stone_bixi),
        ("stone_censer", build_stone_censer),
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
        print("ZHLM8 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM8_DONE")


main()
