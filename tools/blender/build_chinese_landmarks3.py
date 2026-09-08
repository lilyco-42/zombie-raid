"""中式地标 · 知名大场景建筑第三批 (砖石体系, 依旧避开木构飞檐与兽形雕塑)。

  beacon_tower   长城烽火台 (方形砖碉楼, 收分两段 + 箭窗 + 门洞 + 顶垛口)
  gate_platform  城台券门【无楼】(砖城台 + 拱形券门洞 boolean + 顶垛口 + 侧马道台阶)
  huabiao        华表 (须弥座 + 云纹柱 + 横云板 + 承露盘; 不塑蹲兽)
  taihu_rock     太湖石假山 (多球簇错落 + 石座; 园林入门障景, 中式园林无石不成园)
坐标: 原点=底面中心, 正面/门朝 -Y。
运行: blender --background --python tools/blender/build_chinese_landmarks3.py
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


def build_beacon_tower():
    """长城烽火台: 方形砖碉楼, 上下两段收分, 箭窗×2, 南门洞, 顶垛口环。"""
    lower = zh.box("BT_Lower", (4.6, 4.6, 3.4), (0, 0, 2.2), zh.M_BRICK)
    door = zh.box("BT_DoorCut", (1.4, 4.8, 2.1), (0, 0, 1.05), zh.M_BRICK)
    boolean_sub(lower, door)
    upper = zh.box("BT_Upper", (3.8, 3.8, 2.8), (0, 0, 5.3), zh.M_BRICK)
    for sx, tag in ((-1.15, "L"), (1.15, "R")):
        cut = zh.cyl(f"BT_WinCut{tag}", 0.40, 4.0, (sx, 0, 4.30), zh.M_BRICK,
                     verts=14, rot=(PI / 2, 0, 0))
        boolean_sub(upper, cut)
    parts = [
        zh.box("BT_Footing", (5.6, 5.6, 0.50), (0, 0, 0.25), zh.M_BRICK_D),
        lower, upper,
        zh.box("BT_Cap", (4.0, 4.0, 0.22), (0, 0, 6.80), zh.M_BRICK_D),
    ]
    for i in range(-1, 2):
        x = i * 1.15
        parts.append(zh.box(f"BT_CrenelN{i}", (0.70, 0.45, 0.85), (x, 1.75, 7.34), zh.M_BRICK_D))
        parts.append(zh.box(f"BT_CrenelS{i}", (0.70, 0.45, 0.85), (x, -1.75, 7.34), zh.M_BRICK_D))
        parts.append(zh.box(f"BT_CrenelW{i}", (0.45, 0.70, 0.85), (-1.75, x, 7.34), zh.M_BRICK_D))
        parts.append(zh.box(f"BT_CrenelE{i}", (0.45, 0.70, 0.85), (1.75, x, 7.34), zh.M_BRICK_D))
    # 门前三级
    for k in range(3):
        parts.append(zh.box(f"BT_Step{k}", (1.6, 0.5, 0.22),
                            (0, -2.6 - k * 0.5, 0.11 + k * 0.22), zh.M_BRICK_D))
    return zh.join(parts, "beacon_tower")


def build_gate_platform():
    """城台券门 (无楼): 砖城台 + 拱形券门洞 + 顶垛口 + 侧面马道台阶。"""
    plat = zh.box("GP_Platform", (10.0, 6.0, 6.4), (0, 0, 3.2), zh.M_BRICK)
    # 券门: 方洞下段 + 圆柱拱顶 (沿 Y 穿通)
    cut_lo = zh.box("GP_CutLo", (3.2, 6.4, 3.0), (0, 0, 1.5), zh.M_BRICK)
    boolean_sub(plat, cut_lo)
    cut_arc = zh.cyl("GP_CutArc", 1.6, 6.4, (0, 0, 3.0), zh.M_BRICK,
                     verts=24, rot=(PI / 2, 0, 0))
    boolean_sub(plat, cut_arc)
    parts = [
        zh.box("GP_Footing", (10.8, 6.8, 0.4), (0, 0, 0.20), zh.M_BRICK_D),
        plat,
        zh.box("GP_Cap", (10.6, 6.6, 0.35), (0, 0, 6.58), zh.M_BRICK_D),
    ]
    for i in range(-3, 4):
        x = i * 1.35
        parts.append(zh.box(f"GP_CrenelS{i}", (0.70, 0.50, 0.90), (x, -3.05, 7.20), zh.M_BRICK_D))
        parts.append(zh.box(f"GP_CrenelN{i}", (0.70, 0.50, 0.90), (x, 3.05, 7.20), zh.M_BRICK_D))
    # 侧面马道 (5 级上台顶)
    for k in range(5):
        parts.append(zh.box(f"GP_Ramp{k}", (1.4, 2.2, 0.42),
                            (-5.7 + k * 0.9, 0, 0.21 + k * 0.42), zh.M_BRICK_D))
    # 门枕石一对
    parts += [
        zh.box("GP_StoneL", (0.5, 1.0, 0.32), (-1.75, -2.6, 0.16), zh.M_STONE_D),
        zh.box("GP_StoneR", (0.5, 1.0, 0.32), (1.75, -2.6, 0.16), zh.M_STONE_D),
    ]
    return zh.join(parts, "gate_platform")


def build_huabiao():
    """华表: 须弥座 + 云纹柱(三道环) + 横云板 + 承露盘 (不塑蹲兽)。"""
    parts = [
        zh.box("HB_Base", (1.3, 1.3, 0.32), (0, 0, 0.16), zh.M_STONE_D),
        zh.cyl("HB_Pedestal", 0.56, 0.42, (0, 0, 0.53), zh.M_STONE, verts=16),
        zh.cyl("HB_Shaft", 0.28, 5.0, (0, 0, 3.24), zh.M_STONE, verts=20),
    ]
    for k in range(3):
        parts.append(zh.torus(f"HB_Cloud{k}", 0.30, 0.035, (0, 0, 1.6 + k * 1.5),
                              zh.M_STONE_D))
    parts += [
        zh.box("HB_Plate", (1.05, 0.11, 0.52), (0.52, 0, 4.95), zh.M_STONE_D),
        zh.cyl("HB_Dish", 0.52, 0.13, (0, 0, 5.86), zh.M_STONE, verts=24),
        zh.cyl("HB_Top", 0.17, 0.34, (0, 0, 6.10), zh.M_STONE_D, verts=12),
    ]
    return zh.join(parts, "huabiao")


def build_taihu_rock():
    """太湖石假山: 主石 + 副石簇错落 + 石座 (球形簇叠出孔洞凹凸轮廓)。"""
    parts = [zh.box("TR_Base", (2.8, 2.4, 0.24), (0, 0, 0.12), zh.M_STONE_D)]
    rocks = [
        (1.05, (-0.15, 0, 1.05), (1.0, 0.78, 1.35)),
        (0.62, (0.95, 0.35, 0.62), (1.0, 0.9, 1.1)),
        (0.48, (-1.05, -0.30, 0.55), (1.1, 0.85, 1.2)),
        (0.40, (0.35, -0.85, 0.48), (1.0, 1.0, 0.9)),
        (0.30, (-0.55, 0.85, 1.75), (1.0, 1.0, 1.0)),
    ]
    for i, (r, loc, sc) in enumerate(rocks):
        parts.append(zh.sph(f"TR_Rock{i}", r, loc, zh.M_STONE_D, seg=14, ring=9, scale=sc))
    return zh.join(parts, "taihu_rock")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # 注意: import build_chinese 会执行其模块底 main() 并缓存字体句柄,
    # 场景重置会使其失效 (VectorFont removed) → 清缓存待懒重载
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("beacon_tower", build_beacon_tower),
        ("gate_platform", build_gate_platform),
        ("huabiao", build_huabiao),
        ("taihu_rock", build_taihu_rock),
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
        print("ZHLM3 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM3_DONE")


main()
