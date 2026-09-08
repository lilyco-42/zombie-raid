"""中式渐进 · 引路灯 目检 —— 一段 4 格(24m) 设施走廊里的红灯笼灯链。

目的: 验证 chinese_wayfind.gd 的落位在 KayKit 地牢 (4m 层高 / 4x4 地砖 /
4x1 墙) 里是否成立 —— 灯笼是否贴顶、是否偏向"下一格"形成可读的灯链、
出口三盏成簇是否远看就认得出。坐标与游戏落位逻辑同源 (BIAS=1.55, y=3.14)。

运行: blender --background --python tools/blender/render_chinese_wayfind.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    render_to, ROOT)

SV = os.path.join(ROOT, "assets", "static", "vendor")
ZH = os.path.join(SV, "chinese")
DUN = os.path.join(ROOT, "assets", "kaykit", "dungeon")

WALL_H = 4.0          # KayKit dungeon wall 实测高度
CEIL = WALL_H + 0.08
HANG_Y = WALL_H - 0.86   # 灯笼顶沿 +0.86 -> 顶面贴天花板 (与脚本同式)
BIAS = 1.55              # 灯链偏向下一格
EXIT_R = 1.15

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


def lamp(loc, energy, color=(1.0, 0.52, 0.30), radius=6.5):
    """灯笼自身的光 (Blender 里点光, 模拟 Godot OmniLight3D)"""
    ld = bpy.data.lights.new("ZWLight", type="POINT")
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = 0.25
    ob = bpy.data.objects.new("ZWLight", ld)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ---- 壳体: 4 格走廊 (x -12..12, y -3..3), 与 dungeon_builder 同源 ----
XS = [-10.0, -6.0, -2.0, 2.0, 6.0, 10.0]     # 4x4 地砖/4m 墙的铺装中心
for x in XS:
    for y in (-1.5, 1.5):
        put(d("floor_tile_large"), (x, y, 0.03))
        put(d("floor_wood_large_dark"), (x, y, CEIL), rot_x=math.pi)   # 翻面当天花板
for x in XS:
    put(d("wall"), (x, -3.0, 0.0))
    put(d("wall"), (x, 3.0, 0.0))

# ---- 引路灯: 4 格路径, 格心 x = -9/-3/3/9, 灯笼偏向下一格 ----
CELLS = [-9.0, -3.0, 3.0, 9.0]
ceils = [o for o in bpy.data.objects if o.location.z > CEIL - 0.5 and o.type != "LIGHT"]
for i, cx in enumerate(CELLS[:-1]):
    lx = cx + BIAS
    put(z("lantern_red"), (lx, 0.0, HANG_Y))
    lamp((lx, 0.0, HANG_Y - 0.35), 26.0)

# 出口: 三盏成簇 + 更亮
for i in range(3):
    a = math.tau * i / 3.0 + 0.4
    ex = CELLS[-1] + math.cos(a) * EXIT_R
    ey = math.sin(a) * EXIT_R
    put(z("lantern_red"), (ex, ey, HANG_Y))
    lamp((ex, ey, HANG_Y - 0.35), 46.0, (1.0, 0.46, 0.24))

setup_scene()
# 地牢里压暗环境光, 让灯笼成为唯一光源
for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
    lt.data.energy *= 0.10

# 机位 1: 入口端向出口看 —— 灯链是否"指路"
add_camera("Eye", (-11.2, 0.0, 1.72), (8.5, 0.0, 2.55), 26.0)
render_to("zw_wayfind_corridor.png")

# 机位 2: 出口灯簇特写 —— 远距能不能认出"这是出口"
add_camera("Exit", (3.4, 1.4, 2.05), (9.0, 0.0, 2.85), 34.0)
render_to("zw_wayfind_exit.png")

# 机位 3: 俯瞰灯链走向 (藏天花板, 否则只拍到一片瓦)
for o in ceils:
    o.hide_render = True
add_camera("Top", (0.0, -0.6, 26.0), (0.0, 0.0, 2.6), 22.0)
render_to("zw_wayfind_top.png")

print("ZWAYFIND_PV_DONE")
