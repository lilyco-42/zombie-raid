"""中式地标 · 知名大场景建筑第二批 (土/石体系, 依旧避开木构飞檐)。

  tulou           福建土楼【残迹】(圆环夯土墙 24 段×3 层, 南向留门洞, 外嵌窗, 顶部残破 —— 无顶故无需木构瓦顶)
  circular_altar  天坛式圜丘 (三层圆台 + 望柱栏板 + 天心石 + 南向台阶, 纯石作, 上供/仪式场景锚点)
  grotto_cliff    石窟崖壁 (石崖 + 3 座拱形佛龛 boolean 挖洞 + 龛内石座, 空龛不塑像)
坐标: 原点=底面中心, 正面/门朝 -Y。
运行: blender --background --python tools/blender/build_chinese_landmarks2.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PI = math.pi


def extra_materials():
    g = zh.__dict__
    g["M_RAMMED"] = zh.make_material("M_ZH_Rammed", (0.48, 0.36, 0.24), rough=0.95)
    g["M_RAMMED_D"] = zh.make_material("M_ZH_RammedDark", (0.34, 0.25, 0.17), rough=0.95)
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


def build_tulou():
    """福建土楼残迹: 24 段圆环夯土墙 × 3 层, 南向(-Y)留门, 外嵌窗, 顶部参差残破。"""
    parts = []
    R, SEG, LH = 8.3, 24, 3.0
    for i in range(SEG):
        a = 2 * PI * i / SEG
        cx, cy = R * math.cos(a), R * math.sin(a)
        # 南向 (-Y) 留门洞: 角度接近 -90° 的两段跳过底层
        gate = abs(((a + PI / 2 + PI) % (2 * PI)) - PI) < 0.45
        # 确定性残破: 部分段少一层
        levels = 3
        if i % 5 == 0:
            levels = 2
        if i % 7 == 3:
            levels = 1
        for lv in range(levels):
            if gate and lv == 0:
                continue
            z = 1.5 + lv * LH
            parts.append(zh.box(f"TL_W{i}_{lv}", (2.40, 1.4, LH), (cx, cy, z),
                                zh.M_RAMMED, rot=(0, 0, a + PI / 2)))
        # 外嵌窗 (每层一个, 贴外表面)
        for lv in range(min(levels, 3)):
            if lv == 0:
                continue
            parts.append(zh.box(f"TL_Win{i}_{lv}", (0.62, 0.14, 0.72),
                                ((R + 0.72) * math.cos(a), (R + 0.72) * math.sin(a),
                                 1.5 + lv * LH + 0.2),
                                zh.M_RAMMED_D, rot=(0, 0, a + PI / 2)))
    # 门框 (南向)
    parts += [
        zh.box("TL_DoorL", (0.5, 1.4, 3.0), (-1.35, -8.3, 1.5), zh.M_RAMMED_D),
        zh.box("TL_DoorR", (0.5, 1.4, 3.0), (1.35, -8.3, 1.5), zh.M_RAMMED_D),
        zh.box("TL_DoorTop", (3.2, 1.4, 0.45), (0, -8.3, 3.2), zh.M_RAMMED_D),
        # 院内残墙 (内圈隔断遗迹)
        zh.box("TL_Inner", (7.0, 0.5, 1.6), (0, 3.5, 0.8), zh.M_RAMMED_D),
        zh.box("TL_Inner2", (0.5, 6.0, 1.4), (2.2, 0.5, 0.7), zh.M_RAMMED_D),
    ]
    return zh.join(parts, "tulou")


def build_circular_altar():
    """天坛式圜丘: 三层圆台收分 + 望柱栏板 + 天心石 + 南向台阶。"""
    parts = []
    tiers = [(5.0, 0.55, 16), (3.6, 0.55, 12), (2.2, 0.55, 8)]
    z = 0.0
    for ti, (r, h, ncol) in enumerate(tiers):
        parts.append(zh.cyl(f"CA_Tier{ti}", r, h, (0, 0, z + h / 2), zh.M_STONE, verts=48))
        # 望柱 + 栏板 (torus 近似)
        for k in range(ncol):
            a = 2 * PI * k / ncol
            parts.append(zh.cyl(f"CA_Col{ti}_{k}", 0.11, 0.62,
                                ((r - 0.16) * math.cos(a), (r - 0.16) * math.sin(a), z + h + 0.31),
                                zh.M_STONE_D, verts=8))
        parts.append(zh.torus(f"CA_Rail{ti}", r - 0.16, 0.055, (0, 0, z + h + 0.50),
                              zh.M_STONE_D))
        z += h
    parts += [
        zh.cyl("CA_Center", 0.62, 0.07, (0, 0, z + 0.035), zh.M_STONE_D, verts=32),
    ]
    # 南向台阶三级
    for k in range(3):
        parts.append(zh.box(f"CA_Step{k}", (1.9, 0.5, 0.19),
                            (0, -5.0 - k * 0.5, 0.095 + k * 0.19), zh.M_STONE_D))
    return zh.join(parts, "circular_altar")


def build_grotto_cliff():
    """石窟崖壁: 石崖 + 3 座拱形佛龛 (boolean 方洞+拱顶) + 龛内石座。正面朝 -Y。"""
    cliff = zh.box("GC_Cliff", (16.0, 6.0, 9.0), (0, 0, 4.5), zh.M_STONE_D)
    parts = [cliff]
    for i, cx in enumerate((-5.0, 0.0, 5.0)):
        cut_box = zh.box(f"GC_CutBox{i}", (2.5, 3.2, 2.6), (cx, -3.0 + 1.6, 2.4), zh.M_STONE)
        boolean_sub(cliff, cut_box)
        cut_arc = zh.cyl(f"GC_CutArc{i}", 1.25, 2.5, (cx, -3.0 + 1.6, 3.7),
                         zh.M_STONE, verts=20, rot=(PI / 2, 0, 0))
        boolean_sub(cliff, cut_arc)
        # 龛内石座 (空龛不塑像)
        parts.append(zh.box(f"GC_Pedestal{i}", (1.8, 1.4, 0.38), (cx, -2.6, 1.29), zh.M_STONE))
    parts += [
        zh.box("GC_Top1", (6.0, 6.6, 1.3), (-4.5, 0, 9.65), zh.M_STONE_D),
        zh.box("GC_Top2", (5.0, 5.8, 1.6), (3.0, 0.4, 9.8), zh.M_STONE_D),
        zh.box("GC_Foot", (17.0, 7.0, 0.5), (0, 0, 0.25), zh.M_STONE_D),
    ]
    return zh.join(parts, "grotto_cliff")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # 注意: import build_chinese 会执行其模块底 main() 并缓存字体句柄,
    # 场景重置会使其失效 (VectorFont removed) → 清缓存待懒重载
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("tulou", build_tulou),
        ("circular_altar", build_circular_altar),
        ("grotto_cliff", build_grotto_cliff),
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
        print("ZHLM2 ->", path, "verts=", len(obj.data.vertices))
    print("ZHLM2_DONE")


main()
