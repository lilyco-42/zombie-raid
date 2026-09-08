"""中式旧物 · 废料线第一批 (参数化小器物, lyco 例外条款允许自建)。

  thermos_bottle  暖水瓶 (竹壳+铝肩+壶嘴+侧提手, H≈0.45)
  enamel_mug      搪瓷缸 (白瓷缸身+红字环带+侧柄, H≈0.10)
  tin_can         铁皮罐头 (钢身+锈橙纸标+铝盖+拉环, H≈0.12)
  ration_bundle   粮票捆 (纸叠错位+十字纸绳+红印章, H≈0.05)

真实比例 (拾取件), 原点=底面中心。
运行: blender --background --python tools/blender/build_chinese_relics.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PI = math.pi


def extra_materials():
    g = zh.__dict__
    g["M_PAPER"] = zh.make_material("M_ZH_Paper", (0.82, 0.76, 0.62), rough=0.9)
    g["M_BAMBOO"] = zh.make_material("M_ZH_Bamboo", (0.52, 0.41, 0.24), rough=0.85)
    g["M_BAMBOO_D"] = zh.make_material("M_ZH_BambooDark", (0.36, 0.28, 0.16), rough=0.9)


def build_thermos_bottle():
    """暖水瓶: 竹壳圆筒 + 铝肩铝盖 + 斜壶嘴 + 侧提手。"""
    parts = [
        zh.cyl("TH_Shell", 0.11, 0.34, (0, 0, 0.17), zh.M_BAMBOO, verts=16),
        zh.cyl("TH_BandLo", 0.115, 0.02, (0, 0, 0.10), zh.M_BAMBOO_D, verts=16),
        zh.cyl("TH_BandHi", 0.115, 0.02, (0, 0, 0.24), zh.M_BAMBOO_D, verts=16),
        zh.cyl("TH_Shoulder", 0.09, 0.05, (0, 0, 0.365), zh.M_ALU, verts=16),
        zh.cyl("TH_Cap", 0.05, 0.05, (0, 0, 0.415), zh.M_ALU, verts=12),
        zh.cyl("TH_Spout", 0.024, 0.06, (0.06, 0, 0.425), zh.M_ALU,
               verts=10, rot=(0, -0.45, 0)),
        zh.box("TH_HandleV", (0.016, 0.014, 0.16), (0.128, 0, 0.24), zh.M_BAMBOO_D),
        zh.box("TH_HandleT", (0.05, 0.014, 0.016), (0.105, 0, 0.32), zh.M_BAMBOO_D),
        zh.cyl("TH_Base", 0.115, 0.012, (0, 0, 0.006), zh.M_BAMBOO_D, verts=16),
    ]
    return zh.join(parts, "thermos_bottle")


def build_enamel_mug():
    """搪瓷缸: 白瓷缸身 + 红字环带 + 内口 + 侧柄。"""
    parts = [
        zh.cyl("EM_Body", 0.045, 0.09, (0, 0, 0.045), zh.M_ENAMEL, verts=16),
        zh.cyl("EM_Band", 0.047, 0.03, (0, 0, 0.055), zh.M_RED, verts=16),
        zh.cyl("Mug_Rim", 0.040, 0.012, (0, 0, 0.094), zh.M_STONE_D, verts=16),
        zh.box("EM_HandleV", (0.012, 0.010, 0.05), (0.056, 0, 0.05), zh.M_ENAMEL),
        zh.box("EM_HandleT1", (0.020, 0.010, 0.012), (0.043, 0, 0.072), zh.M_ENAMEL),
        zh.box("EM_HandleT2", (0.020, 0.010, 0.012), (0.043, 0, 0.028), zh.M_ENAMEL),
    ]
    return zh.join(parts, "enamel_mug")


def build_tin_can():
    """铁皮罐头: 钢身 + 锈橙纸标 + 铝顶盖 + 拉环。"""
    parts = [
        zh.cyl("TC_Body", 0.050, 0.11, (0, 0, 0.055), zh.M_STEEL, verts=16),
        zh.cyl("TC_Label", 0.052, 0.07, (0, 0, 0.052), zh.M_RUST, verts=16),
        zh.cyl("TC_Lid", 0.050, 0.012, (0, 0, 0.116), zh.M_ALU, verts=16),
        zh.box("TC_Pull", (0.022, 0.008, 0.005), (0.012, 0, 0.126), zh.M_ALU),
    ]
    return zh.join(parts, "tin_can")


def build_ration_bundle():
    """粮票捆: 两叠错位纸 + 十字纸绳 + 红印章。"""
    parts = [
        zh.box("RB_StackLo", (0.11, 0.07, 0.028), (0, 0, 0.014), zh.M_PAPER),
        zh.box("RB_StackHi", (0.10, 0.065, 0.020), (0.005, 0.004, 0.038), zh.M_PAPER,
               rot=(0, 0, 0.08)),
        zh.box("RB_TieX", (0.125, 0.008, 0.003), (0, 0, 0.031), zh.M_BAMBOO_D),
        zh.box("RB_TieY", (0.008, 0.082, 0.003), (0, 0, 0.031), zh.M_BAMBOO_D),
        zh.box("RB_Stamp", (0.022, 0.022, 0.002), (0.022, -0.012, 0.049), zh.M_RED),
    ]
    return zh.join(parts, "ration_bundle")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("thermos_bottle", build_thermos_bottle),
        ("enamel_mug", build_enamel_mug),
        ("tin_can", build_tin_can),
        ("ration_bundle", build_ration_bundle),
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
        print("ZHRELIC ->", path, "verts=", len(obj.data.vertices))
    print("ZHRELIC_DONE")


main()
