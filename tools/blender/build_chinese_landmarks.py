"""中式地标 · 知名大场景建筑第一批 (砖石体系, 全部避开木构飞檐 —— 见 lyco 技能例外条款)。

  greatwall_tower 长城敌台 (墙段+马道+垛口+券门敌楼+箭窗, boolean 券洞)
  brick_pagoda   密檐式砖塔 (大雁塔式: 逐层收分 + **砖叠涩檐** —— 砖仿木的檐是叠涩砖,
                  不是木飞檐, 属于高信心简单几何; 塔刹相轮宝珠)
  stone_bridge   敞肩石拱桥 (赵州桥式: 主拱 + 两肩小拱 + 弧背桥面 + 望柱栏板)
坐标: 原点=底面中心, 装饰/正面朝 -Y。
运行: blender --background --python tools/blender/build_chinese_landmarks.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PI = math.pi


def extra_materials():
    g = zh.__dict__
    g["M_BRICK"] = zh.make_material("M_ZH_Brick", (0.44, 0.40, 0.34), rough=0.95)
    g["M_BRICK_D"] = zh.make_material("M_ZH_BrickDark", (0.32, 0.29, 0.25), rough=0.95)
    g["M_WATER"] = zh.make_material("M_ZH_Water", (0.05, 0.07, 0.08), rough=0.15)


def boolean_sub(target, cutter):
    """目标挖去 cutter (券洞/箭窗)。"""
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def build_greatwall_tower():
    """长城敌台: 12m 墙段 + 马道 + 外侧垛口 + 券门敌楼 + 箭窗。"""
    parts = [
        zh.box("GW_Wall", (12.0, 2.4, 4.2), (0, 0, 2.1), zh.M_BRICK),
        zh.box("GW_Walk", (12.0, 2.6, 0.18), (0, 0, 4.29), zh.M_BRICK_D),
        zh.box("GW_ParapetIn", (12.0, 0.35, 0.70), (0, -1.05, 4.73), zh.M_BRICK_D),
        zh.box("GW_Footing", (12.6, 3.0, 0.3), (0, 0, 0.15), zh.M_BRICK_D),
    ]
    # 外侧垛口 (每 1.4m 一个)
    for i in range(-4, 5):
        parts.append(zh.box(f"GW_Crenel{i}", (0.70, 0.50, 0.90),
                            (i * 1.4, 1.10, 4.83), zh.M_BRICK_D))
    # 敌楼本体 (比墙厚, 骑在墙上)
    tower = zh.box("GW_Tower", (6.4, 4.6, 7.2), (0, 0.3, 3.6), zh.M_BRICK)
    gate = zh.cyl("GW_GateCut", 1.05, 5.0, (0, 0.3, 1.70), zh.M_BRICK,
                  verts=24, rot=(PI / 2, 0, 0))
    boolean_sub(tower, gate)
    for sx, tag in ((-1.9, "L"), (1.9, "R")):
        win = zh.cyl(f"GW_WinCut{tag}", 0.42, 5.0, (sx, 0.3, 4.60), zh.M_BRICK,
                     verts=16, rot=(PI / 2, 0, 0))
        boolean_sub(tower, win)
    parts.append(tower)
    parts += [
        zh.box("GW_TowerTop", (6.8, 5.0, 0.25), (0, 0.3, 7.33), zh.M_BRICK_D),
    ]
    # 敌楼顶垛口环
    for i in range(-2, 3):
        x = i * 1.3
        parts.append(zh.box(f"GW_TopCrenelN{i}", (0.70, 0.45, 0.85), (x, 2.75, 7.90), zh.M_BRICK_D))
        parts.append(zh.box(f"GW_TopCrenelS{i}", (0.70, 0.45, 0.85), (x, -2.15, 7.90), zh.M_BRICK_D))
    for j in range(-1, 2):
        y = 0.3 + j * 1.3
        parts.append(zh.box(f"GW_TopCrenelW{j}", (0.45, 0.70, 0.85), (-3.05, y, 7.90), zh.M_BRICK_D))
        parts.append(zh.box(f"GW_TopCrenelE{j}", (0.45, 0.70, 0.85), (3.05, y, 7.90), zh.M_BRICK_D))
    # 门前台阶三级
    for k in range(3):
        parts.append(zh.box(f"GW_Step{k}", (2.0, 0.5, 0.22),
                            (0, -2.6 - k * 0.5, 0.11 + k * 0.22), zh.M_BRICK_D))
    return zh.join(parts, "greatwall_tower")


def build_brick_pagoda():
    """密檐式砖塔: 5 层逐层收分 + 砖叠涩檐 + 塔刹相轮宝珠。"""
    parts = [
        zh.box("PG_Plinth", (5.2, 5.2, 0.50), (0, 0, 0.25), zh.M_STONE_D),
        zh.box("PG_Pedestal", (4.8, 4.8, 0.35), (0, 0, 0.675), zh.M_STONE),
    ]
    s, base_z = 3.6, 0.85
    for i in range(5):
        z0 = base_z + i * 1.7
        parts.append(zh.box(f"PG_Body{i}", (s, s, 1.5), (0, 0, z0 + 0.75), zh.M_BRICK))
        # 券窗 (南北贴面暗块)
        parts.append(zh.box(f"PG_WinS{i}", (0.55, 0.06, 0.62),
                            (0, -s / 2 - 0.01, z0 + 0.95), zh.M_BRICK_D))
        parts.append(zh.box(f"PG_WinN{i}", (0.55, 0.06, 0.62),
                            (0, s / 2 + 0.01, z0 + 0.95), zh.M_BRICK_D))
        # 砖叠涩檐: 三层逐层外挑 (砖仿木, 非木飞檐)
        for k in range(3):
            w = s + 0.22 + k * 0.30
            parts.append(zh.box(f"PG_Eave{i}_{k}", (w, w, 0.13),
                                (0, 0, z0 + 1.50 + 0.07 + k * 0.13), zh.M_BRICK_D))
        s -= 0.5
    top = base_z + 5 * 1.7 + 0.10
    parts += [
        zh.cyl("PG_Finial", 0.16, 1.20, (0, 0, top + 0.60), zh.M_STONE, verts=12),
        zh.sph("PG_Pearl", 0.18, (0, 0, top + 1.32), zh.M_GOLD if zh.__dict__.get("M_GOLD") else zh.M_STONE,
               seg=12, ring=8),
    ]
    for k in range(3):
        parts.append(zh.torus(f"PG_Ring{k}", 0.24 - k * 0.04, 0.028,
                              (0, 0, top + 0.35 + k * 0.16), zh.M_GOLD
                              if zh.__dict__.get("M_GOLD") else zh.M_STONE))
    return zh.join(parts, "brick_pagoda")


def build_stone_bridge():
    """敞肩石拱桥: 主拱 + 两肩小拱 + 弧背桥面 + 望柱栏板。"""
    parts = [zh.box("SB_Abutment", (9.0, 2.8, 0.40), (0, 0, 0.20), zh.M_STONE_D)]
    # 主拱券 (半圆 r=3.2, 段长 1.30 ≈ 弧长 1.12 略叠, 消段缝)
    for i in range(9):
        a = PI * (i / 8.0)          # 0..PI
        x = -3.2 * math.cos(a)
        z = 0.40 + 3.2 * math.sin(a)
        parts.append(zh.box(f"SB_Arch{i}", (1.30, 2.4, 0.30), (x, 0, z),
                            zh.M_STONE, rot=(0, 0, -a + PI / 2)))
    # 两肩小拱
    for sx in (-2.45, 2.45):
        for i in range(5):
            a = PI * (i / 4.0)
            x = sx - 0.95 * math.cos(a)
            z = 1.35 + 0.95 * math.sin(a)
            parts.append(zh.box(f"SB_Spandrel{sx}_{i}", (0.70, 2.4, 0.24), (x, 0, z),
                                zh.M_STONE_D, rot=(0, 0, -a + PI / 2)))
    # 弧背桥面 (7 段)
    for i in range(7):
        x = -3.6 + i * 1.2
        z = 0.55 + 1.85 * (1.0 - (x / 4.0) ** 2)
        slope = -2 * 1.85 * x / (4.0 ** 2) / 1.2
        parts.append(zh.box(f"SB_Deck{i}", (1.25, 2.4, 0.22), (x, 0, z),
                            zh.M_STONE, rot=(0, 0, math.atan(slope) * 0.5)))
        # 望柱 + 栏板
        if i % 2 == 0:
            for sy in (-1.05, 1.05):
                parts.append(zh.cyl(f"SB_Post{i}_{sy}", 0.07, 0.55, (x, sy, z + 0.40),
                                    zh.M_STONE, verts=8))
    for sy in (-1.05, 1.05):
        for k, (x0, z0) in enumerate([(-2.4, 1.15), (0.0, 1.85), (2.4, 1.15)]):
            parts.append(zh.box(f"SB_Rail{sy}_{k}", (2.4, 0.10, 0.14), (x0, sy, z0 + 0.62),
                                zh.M_STONE_D))
    return zh.join(parts, "stone_bridge")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # 注意: import build_chinese 会执行其模块底 main() 并缓存字体句柄,
    # 场景重置会使其失效 (VectorFont removed) → 清缓存待懒重载
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("greatwall_tower", build_greatwall_tower),
        ("brick_pagoda", build_brick_pagoda),
        ("stone_bridge", build_stone_bridge),
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
        print("ZHLM ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM_DONE")


main()
