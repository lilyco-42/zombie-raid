"""中式地标 · 长城体系第二批 (补缺口四件; 依旧砖石券拱, 避开木构飞檐)。

  greatwall_ramp          登城券门段 (8m 模块: 墙身 + 内侧券门洞 + 砖砌登城踏道; 女墙中开豁口接踏道)
  greatwall_hollow_tower  空心敌楼 (基座 + 中室[券门×1 箭窗×6] + 楼板开木梯口 + 台顶垛口环)
  greatwall_ruin          残破断墙段 (8m: 塌顶锯齿 + 中段豁口 + 残垣 + 散落砖石)
  greatwall_section2      细节墙段 (8m: 同剖面 + 垛口射眼 + 内侧排水沟 + 外侧吐水嘴)
  gw_barrier_wall         障墙 (马道横护墙, 带射孔; 坡道段侧面护兵)

真实形制参照: 墙高 6-9m / 马道宽 4m / 垛口(雉堞)高 1.7-2m 带射眼 / 女墙高约 1m /
券门内石阶登城 / 吐水嘴排水 / 障墙护坡 (明长城 戚继光空心敌台制)。
坐标: 原点=底面中心, 墙沿 X 拼接, 外侧(垛口)朝 +Y, 内侧(女墙/登城)朝 -Y。
运行: blender --background --python tools/blender/build_chinese_landmarks13.py
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


def boolean_sub(target, cutter):
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


# ---------------------------------------------------------------- 1 登城券门段
def build_greatwall_ramp():
    """登城券门段: 标准墙身 + 内侧券门洞 + 砖砌登城踏道 (女墙中留豁口)。"""
    lower = zh.box("GR_Lower", (8.0, 3.2, 2.60), (0, 0, 1.90), zh.M_BRICK)
    # 券门: 方洞下段 + 圆柱拱顶 (沿 Y 穿通墙身)
    boolean_sub(lower, zh.box("GR_CutLo", (1.90, 3.4, 2.10), (0, 0, 1.05), zh.M_BRICK))
    boolean_sub(lower, zh.cyl("GR_CutArc", 0.85, 3.4, (0, 0, 2.10), zh.M_BRICK,
                              verts=24, rot=(PI / 2, 0, 0)))
    parts = [
        zh.box("GR_Footing", (8.4, 3.6, 0.60), (0, 0, 0.30), zh.M_BRICK_D),
        lower,
        zh.box("GR_Upper", (7.7, 2.7, 2.20), (0, 0.1, 4.30), zh.M_BRICK),
        zh.box("GR_Walk", (8.2, 3.0, 0.18), (0, 0.05, 5.49), zh.M_BRICK_D),
    ]
    # 外侧垛口 (每 1.4m 一齿)
    for i in range(-3, 4):
        parts.append(zh.box(f"GR_Crenel{i}", (0.72, 0.50, 0.92),
                            (i * 1.4, 1.32, 6.04), zh.M_BRICK_D))
    # 内侧女墙: 中段留 2.4m 豁口, 让踏道接上马道
    parts += [
        zh.box("GR_ParapetL", (2.8, 0.35, 0.72), (-2.8, -1.28, 5.94), zh.M_BRICK_D),
        zh.box("GR_ParapetR", (2.8, 0.35, 0.72), (2.8, -1.28, 5.94), zh.M_BRICK_D),
    ]
    # 砖砌登城踏道: 自内侧地面 -5.5 起, 14 级, 每级升 0.40 / 进 0.286, 顶端接马道
    steps, rise, run = 14, 0.40, 0.286
    for k in range(steps):
        h = rise * (k + 1)
        parts.append(zh.box(f"GR_Step{k}", (2.2, run, h),
                            (0, -5.5 + k * run + run / 2, h / 2), zh.M_BRICK_D))
    return zh.join(parts, "greatwall_ramp")


# ------------------------------------------------------------- 2 空心敌楼(骑墙)
def build_greatwall_hollow_tower():
    """空心敌楼: 基座 + 中室(券门×1 + 箭窗×6) + 楼板开木梯口 + 台顶垛口环。"""
    parts = [zh.box("HT_Footing", (9.4, 7.4, 0.60), (0, 0, 0.30), zh.M_BRICK_D)]

    # ---- 中室: 外墙 9.0×7.0, 厚 1.2, 室高 4.2 (z 0.6→4.8)
    wall_s = zh.box("HT_WallS", (6.6, 1.2, 4.2), (0, -2.9, 2.70), zh.M_BRICK)
    boolean_sub(wall_s, zh.box("HT_DoorLo", (1.80, 1.6, 2.40), (0, -2.9, 1.80), zh.M_BRICK))
    boolean_sub(wall_s, zh.cyl("HT_DoorArc", 0.90, 1.6, (0, -2.9, 3.00), zh.M_BRICK,
                               verts=24, rot=(PI / 2, 0, 0)))

    wall_n = zh.box("HT_WallN", (6.6, 1.2, 4.2), (0, 2.9, 2.70), zh.M_BRICK)
    wall_w = zh.box("HT_WallW", (1.2, 7.0, 4.2), (-3.9, 0, 2.70), zh.M_BRICK)
    wall_e = zh.box("HT_WallE", (1.2, 7.0, 4.2), (3.9, 0, 2.70), zh.M_BRICK)
    # 箭窗 (每面 2 孔: 方洞 + 拱顶)
    for k, x in enumerate((-2.0, 2.0)):                      # 南北面: 沿 X
        boolean_sub(wall_n, zh.box(f"HT_ArwN{k}Lo", (0.90, 1.6, 0.90), (x, 2.9, 2.50), zh.M_BRICK))
        boolean_sub(wall_n, zh.cyl(f"HT_ArwN{k}Arc", 0.45, 1.6, (x, 2.9, 2.95), zh.M_BRICK,
                                   verts=16, rot=(PI / 2, 0, 0)))
    for k, y in enumerate((-1.8, 1.8)):                      # 东西面: 沿 Y
        for tag, wall, sx in (("W", wall_w, -3.9), ("E", wall_e, 3.9)):
            boolean_sub(wall, zh.box(f"HT_Arw{tag}{k}Lo", (1.6, 0.90, 0.90), (sx, y, 2.50), zh.M_BRICK))
            boolean_sub(wall, zh.cyl(f"HT_Arw{tag}{k}Arc", 0.45, 1.6, (sx, y, 2.95), zh.M_BRICK,
                                     verts=16, rot=(PI / 2, 0, 0)))
    parts += [wall_s, wall_n, wall_w, wall_e]

    # ---- 中室顶(楼板) + 木梯口
    slab = zh.box("HT_Slab", (9.0, 7.0, 0.50), (0, 0, 5.05), zh.M_BRICK_D)
    boolean_sub(slab, zh.box("HT_LadderHole", (1.4, 1.4, 0.9), (2.6, 1.8, 5.05), zh.M_BRICK))
    parts.append(slab)

    # ---- 台顶 + 铺面 + 垛口环
    parts += [
        zh.box("HT_Top", (8.4, 6.4, 2.60), (0, 0, 6.60), zh.M_BRICK),
        zh.box("HT_Deck", (8.6, 6.6, 0.18), (0, 0, 7.99), zh.M_BRICK_D),
    ]
    for i in range(-3, 4):                                   # 南北向垛口
        x = i * 1.3
        parts.append(zh.box(f"HT_CrenN{i}", (0.70, 0.50, 0.95), (x, 2.95, 8.55), zh.M_BRICK_D))
        parts.append(zh.box(f"HT_CrenS{i}", (0.70, 0.50, 0.95), (x, -2.95, 8.55), zh.M_BRICK_D))
    for j in range(-2, 3):                                   # 东西向垛口
        y = j * 1.3
        parts.append(zh.box(f"HT_CrenW{j}", (0.50, 0.70, 0.95), (-3.95, y, 8.55), zh.M_BRICK_D))
        parts.append(zh.box(f"HT_CrenE{j}", (0.50, 0.70, 0.95), (3.95, y, 8.55), zh.M_BRICK_D))
    return zh.join(parts, "greatwall_hollow_tower")


# ----------------------------------------------------------------- 3 残破断墙段
def build_greatwall_ruin():
    """残破断墙段: 塌顶锯齿 + 中段豁口 + 残垣 + 散落砖石。"""
    parts = [
        zh.box("RU_FootL", (5.0, 3.6, 0.50), (-1.5, 0, 0.25), zh.M_BRICK_D),
        zh.box("RU_FootR", (2.0, 3.0, 0.40), (3.0, 0.2, 0.20), zh.M_BRICK_D),
        zh.box("RU_LowerL", (4.6, 3.0, 2.40), (-1.7, 0, 1.70), zh.M_BRICK),
        zh.box("RU_UpperL", (4.2, 2.5, 1.80), (-1.9, 0.05, 3.80), zh.M_BRICK),
        zh.box("RU_StubR", (2.4, 2.8, 1.60), (3.2, 0.1, 1.10), zh.M_BRICK),
        zh.box("RU_WalkL", (4.2, 2.4, 0.15), (-1.9, 0.05, 4.75), zh.M_BRICK_D),
        zh.box("RU_Parapet", (3.0, 0.30, 0.50), (-2.5, -1.20, 5.10), zh.M_BRICK_D),
    ]
    # 塌顶锯齿 (高低错落的残齿)
    for k, (x, h) in enumerate(((-3.4, 0.90), (-2.3, 0.45), (-1.2, 1.15), (-0.1, 0.60))):
        parts.append(zh.box(f"RU_Jag{k}", (0.62, 0.46, h), (x, 1.20, 4.72 + h / 2), zh.M_BRICK_D))
    # 散落砖石 (确定性伪随机, 保证可复现)
    for k, (dx, dy, s) in enumerate(((-3.0, -2.3, 0.55), (-1.6, -2.9, 0.40), (-0.4, -2.5, 0.48),
                                     (1.4, -2.9, 0.36), (2.6, -2.4, 0.50), (3.6, -1.9, 0.42),
                                     (-2.4, 2.6, 0.45), (0.6, 2.8, 0.38))):
        parts.append(zh.box(f"RU_Rubble{k}", (s, s * 0.70, s * 0.55),
                            (dx, dy, s * 0.27), zh.M_BRICK_D, rot=(0, 0, k * 0.6)))
    return zh.join(parts, "greatwall_ruin")


# --------------------------------------------------------- 4 细节墙段(射眼/吐水嘴)
def build_greatwall_section2():
    """细节墙段: 标准剖面 + 垛口射眼(0.5m 竖孔) + 内侧排水沟 + 外侧吐水嘴×2。"""
    parts = [
        zh.box("G2_Footing", (8.4, 3.6, 0.60), (0, 0, 0.30), zh.M_BRICK_D),
        zh.box("G2_Lower", (8.0, 3.2, 2.60), (0, 0, 1.90), zh.M_BRICK),
        zh.box("G2_Upper", (7.7, 2.7, 2.20), (0, 0.1, 4.30), zh.M_BRICK),
        zh.box("G2_Walk", (8.2, 3.0, 0.18), (0, 0.05, 5.49), zh.M_BRICK_D),
        zh.box("G2_ParapetIn", (8.0, 0.35, 0.72), (0, -1.28, 5.94), zh.M_BRICK_D),
        # 内侧排水沟 (马道里缘凹槽)
        zh.box("G2_Gutter", (8.0, 0.22, 0.10), (0, -1.13, 5.62), zh.M_BRICK_D),
    ]
    # 外侧垛口: 下段 + 两侧垛墩 + 顶部过梁 → 中间留射眼 (0.32 宽 × 0.34 高)
    for i in range(-3, 4):
        x = i * 1.4
        parts += [
            zh.box(f"G2_Cren{i}Lo", (0.72, 0.50, 0.42), (x, 1.32, 5.79), zh.M_BRICK_D),
            zh.box(f"G2_Cren{i}PL", (0.20, 0.50, 0.50), (x - 0.26, 1.32, 6.25), zh.M_BRICK_D),
            zh.box(f"G2_Cren{i}PR", (0.20, 0.50, 0.50), (x + 0.26, 1.32, 6.25), zh.M_BRICK_D),
            zh.box(f"G2_Cren{i}Top", (0.72, 0.50, 0.16), (x, 1.32, 6.42), zh.M_BRICK_D),
        ]
    # 吐水嘴 (外侧挑出石槽, 每 4m 一个, 外倾)
    for k, x in enumerate((-2.0, 2.0)):
        parts.append(zh.box(f"G2_Spout{k}", (0.40, 1.00, 0.26), (x, 2.00, 5.15),
                            zh.M_STONE_D, rot=(-0.30, 0, 0)))
    return zh.join(parts, "greatwall_section2")


# ------------------------------------------------------------------- 5 障墙
def build_gw_barrier_wall():
    """障墙: 马道上的横向护墙 (坡道段侧面护兵), 中段开射孔。"""
    parts = [
        zh.box("BW_Plinth", (0.60, 3.2, 0.12), (0, 0, 0.06), zh.M_BRICK_D),
        zh.box("BW_Lower", (0.45, 3.0, 0.50), (0, 0, 0.37), zh.M_BRICK),
        zh.box("BW_PostL", (0.45, 1.35, 0.65), (0, -0.825, 0.895), zh.M_BRICK),
        zh.box("BW_PostR", (0.45, 1.35, 0.65), (0, 0.825, 0.895), zh.M_BRICK),
        zh.box("BW_Lintel", (0.45, 3.0, 0.18), (0, 0, 1.13), zh.M_BRICK_D),
    ]
    return zh.join(parts, "gw_barrier_wall")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # import build_chinese 会执行其模块底 main() 并缓存字体句柄, 场景重置使其失效 → 清缓存
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("greatwall_ramp", build_greatwall_ramp),
        ("greatwall_hollow_tower", build_greatwall_hollow_tower),
        ("greatwall_ruin", build_greatwall_ruin),
        ("greatwall_section2", build_greatwall_section2),
        ("gw_barrier_wall", build_gw_barrier_wall),
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
        print("ZHLM13 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM13_DONE")


main()
