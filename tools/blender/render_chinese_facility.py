"""中式渐进 · 设施篇 目检 —— 一间 6m 设施单元里的中式道具与 KayKit 墙的尺寸对照。

目的: 验证 chinese_facility.gd 用的那批件在 4m 层高 / 4x4 地板砖的 KayKit
地牢里比例是否成立 (悬空/穿墙/比例失衡一眼看出)。坐标与游戏落位逻辑同源。

运行: blender --background --python tools/blender/render_chinese_facility.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    render_to, ROOT)

SV = os.path.join(ROOT, "assets", "static", "vendor")
ZH = os.path.join(SV, "chinese")
DUN = os.path.join(ROOT, "assets", "kaykit", "dungeon")

WALL_H = 4.0        # KayKit dungeon wall 实测高度
WALL_FACE = 2.27    # 墙内表面到格心 (脚本同值)
CEIL = WALL_H + 0.08

bpy.ops.wm.read_factory_settings(use_empty=True)


def put(path, loc=(0.0, 0.0, 0.0), rot_z=0.0, scale=1.0, rot_x=0.0):
    objs = import_gltf(path)
    if not objs:
        print("IMPORT FAIL:", path)
        return []
    for o in objs:
        o.location.x += loc[0]
        o.location.y += loc[1]
        o.location.z += loc[2]
        if rot_z:
            o.rotation_euler.z += rot_z
        if rot_x:
            o.rotation_euler.x += rot_x
        if scale != 1.0:
            o.scale = (o.scale[0] * scale, o.scale[1] * scale, o.scale[2] * scale)
    return objs


def d(name):
    return os.path.join(DUN, name + ".glb")


def z(name):
    return os.path.join(ZH, name + ".glb")


# ---- 壳体: 4x4 地板 + 天花板 + 两面墙 (-Y / -X), 与 dungeon_builder 一致 ----
put(d("floor_tile_large"), (0, 0, 0))
ceil_objs = put(d("floor_wood_large_dark"), (0, 0, CEIL), rot_x=math.pi)   # 翻面当天花板
for x in (-2.0, 2.0):
    put(d("wall"), (x, -3.0, 0))
for y in (-2.0, 2.0):
    put(d("wall"), (-3.0, y, 0), rot_z=math.pi * 0.5)

# ---- 中式落位 (与 chinese_facility.gd 同坐标) ----
put(z("roller_door"), (0.0, -WALL_FACE, 0.0), scale=0.95)
put(z("slogan_safety"), (-WALL_FACE, 0.8, 1.15), rot_z=math.pi * 0.5)
put(z("lantern_red"), (1.2, -1.2, WALL_H - 0.86))
put(z("offering_table"), (-1.2, -1.45, 0.0))
put(z("incense_burner"), (-1.2, -1.45, 0.98))
put(z("paper_ash"), (-1.2, -0.6, 0.0))
put(z("ba_xian_table"), (1.0, 1.2, 0.0))
for i in range(4):
    a = math.tau * i / 4.0 + 0.4
    put(z("stool"), (1.0 + math.cos(a) * 0.95, 1.2 + math.sin(a) * 0.95, 0.0),
        rot_z=a + math.pi)
put(z("water_vat"), (-1.55, 1.55, 0.0))
put(d("torch_lit"), (1.85, -1.85, WALL_H * 0.68))

def fill_light(name, loc, energy, size=2.4):
    ld = bpy.data.lights.new(name, type="AREA")
    ld.energy = energy
    ld.size = size
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    return ob

setup_scene()
# 单元被封死 (地板+顶+两面墙), 需要内部补光, 否则全黑
fill_light("FillCeil", (0.0, 0.0, 3.9), 320.0)
fill_light("FillCorner", (1.9, 1.9, 2.6), 120.0)

# 机位 1: 单元内斜角, 一眼看卷帘门+标语牌+祭祀角+桌椅
add_camera("Eye", (2.25, 2.25, 2.45), (-1.2, -1.3, 1.0), 22.0)
render_to("zf_facility_eye.png")

# 机位 2: 俯瞰布局 (查有没有悬空/穿墙/比例失衡)
for o in ceil_objs:
    o.hide_render = True
add_camera("Top", (0.0, -0.4, 7.6), (0.0, 0.0, 0.6), 32.0)
render_to("zf_facility_top.png")

print("ZFFAC_PV_DONE")
