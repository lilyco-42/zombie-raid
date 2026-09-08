"""中式渐进式改编 Phase 2: 圆明园遗址 × 生活器物 9 件 (低模, 盒/柱/环几何)。

设计依据 docs/map_design_method.md §3 (高信心简单件例外条款):
  遗址类  dashuifa 大水法残迹 (双柱+残拱+倒伏构件+水池沿)
          ruin_columns 残柱阵 (5 柱, 高低参差)
          moon_gate 月洞门 (3.8×0.5×3.4 墙模块, 圆洞 boolean + 灰砖环)
          screen_wall 照壁 (壁心+碗心石+壁帽)
          stele 石碑 (圆首+「永昌」红字, simhei 字模)
  器物类  incense_burner 青铜三足香炉 / ba_xian_table 八仙桌
          stool 方凳 / water_vat 大水缸
飞檐/斗拱/瓦作不在自建范围 (重灾区, 待收编开源包)。
运行: blender --background --python tools/blender/build_chinese_phase2.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PI = math.pi


def extra_materials():
    g = zh.__dict__
    g["M_MARBLE"] = zh.make_material("M_ZH_Marble", (0.62, 0.61, 0.57), rough=0.85)
    g["M_BRONZE"] = zh.make_material("M_ZH_Bronze", (0.34, 0.27, 0.17), rough=0.45, metal=0.7)
    g["M_LACQ"] = zh.make_material("M_ZH_Lacquer", (0.22, 0.12, 0.08), rough=0.5)
    g["M_JAR"] = zh.make_material("M_ZH_Jar", (0.13, 0.12, 0.115), rough=0.8)
    g["M_WATER"] = zh.make_material("M_ZH_Water", (0.05, 0.07, 0.08), rough=0.15)


def boolean_sub(target, cutter):
    """目标挖去 cutter (月洞门圆洞)。"""
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def build_dashuifa():
    """大水法残迹: 双柱 + 左半残拱 (右半坍塌) + 倒伏柱身/柱础 + 水池残沿。"""
    parts = [
        zh.box("DF_Plinth", (3.4, 1.4, 0.30), (0, 0, 0.15), zh.M_STONE_D),
        zh.box("DF_Basin", (1.6, 0.5, 0.35), (0, 1.05, 0.18), zh.M_STONE_D),
    ]
    for sx in (-1.25, 1.25):
        parts += [
            zh.box(f"DF_Base{sx}", (0.62, 0.62, 0.22), (sx, 0, 0.41), zh.M_STONE),
            zh.cyl(f"DF_Shaft{sx}", 0.20, 2.5, (sx, 0, 1.76), zh.M_MARBLE, verts=16),
            zh.box(f"DF_Cap{sx}", (0.56, 0.56, 0.16), (sx, 0, 3.09), zh.M_STONE),
        ]
    # 左半残拱: 三段渐起, 右端断口
    parts += [
        zh.box("DF_Arc1", (0.55, 0.42, 0.20), (-1.00, 0, 3.06), zh.M_MARBLE, rot=(0, 0, -0.22)),
        zh.box("DF_Arc2", (0.50, 0.42, 0.20), (-0.62, 0, 3.22), zh.M_MARBLE, rot=(0, 0, -0.45)),
        zh.box("DF_Arc3", (0.42, 0.42, 0.20), (-0.28, 0, 3.30), zh.M_MARBLE, rot=(0, 0, -0.68)),
    ]
    # 坍塌物: 倒伏柱身 + 滚落柱础 (在台基上)
    parts += [
        zh.cyl("DF_FallenShaft", 0.19, 1.1, (0.55, 0.55, 0.49), zh.M_MARBLE, verts=14,
               rot=(0, PI / 2, 0)),
        zh.box("DF_FallenCap", (0.52, 0.50, 0.15), (-0.25, 0.72, 0.38), zh.M_STONE, rot=(0, 0, 0.4)),
        zh.box("DF_Rubble1", (0.40, 0.35, 0.22), (1.05, 0.62, 0.41), zh.M_STONE_D, rot=(0, 0, 0.7)),
    ]
    return zh.join(parts, "dashuifa")


def build_ruin_columns():
    """残柱阵: 5 柱高低参差, 断柱顶部带倾斜断口块。"""
    parts = []
    cols = [(0.0, 2.4, True), (0.9, 1.6, False), (1.8, 2.8, True),
            (2.7, 0.9, False), (3.6, 2.1, True)]
    for i, (x, h, capped) in enumerate(cols):
        rz = ((i * 37) % 9 - 4) * 0.02
        parts.append(zh.box(f"RC_Base{i}", (0.55, 0.55, 0.18), (x, 0, 0.09), zh.M_STONE_D))
        parts.append(zh.cyl(f"RC_Shaft{i}", 0.19, h, (x, 0, 0.18 + h / 2), zh.M_MARBLE,
                            verts=14, rot=(0, 0, rz)))
        if capped:
            parts.append(zh.box(f"RC_Cap{i}", (0.50, 0.50, 0.14),
                                (x, 0, 0.18 + h + 0.07), zh.M_STONE))
        else:
            parts.append(zh.box(f"RC_Break{i}", (0.30, 0.26, 0.10),
                                (x + 0.05, 0.04, 0.18 + h + 0.03), zh.M_MARBLE,
                                rot=(0.15, 0.1, rz)))
    return zh.join(parts, "ruin_columns")


def build_moon_gate():
    """月洞门: 墙模块挖圆洞 + 灰砖环 + 顶枋 + 门枕石。装饰面朝 ±Y。"""
    wall = zh.box("MG_Wall", (3.8, 0.5, 3.2), (0, 0, 1.6), zh.M_STONE_D)
    cutter = zh.cyl("MG_Hole", 1.05, 1.0, (0, 0, 1.45), zh.M_STONE, verts=32,
                    rot=(PI / 2, 0, 0))
    boolean_sub(wall, cutter)
    parts = [
        wall,
        zh.torus("MG_Ring", 1.08, 0.075, (0, 0, 1.45), zh.M_STONE, rot=(PI / 2, 0, 0)),
        zh.box("MG_Lintel", (4.0, 0.56, 0.20), (0, 0, 3.30), zh.M_STONE_D),
        zh.box("MG_PostL", (0.30, 0.70, 0.25), (-1.62, 0, 0.125), zh.M_STONE_D),
        zh.box("MG_PostR", (0.30, 0.70, 0.25), (1.62, 0, 0.125), zh.M_STONE_D),
    ]
    return zh.join(parts, "moon_gate")


def build_screen_wall():
    """照壁: 底座 + 壁心 + 壁帽 + 碗心石 (装饰面朝 -Y)。"""
    parts = [
        zh.box("SW_Base", (3.0, 0.72, 0.28), (0, 0, 0.14), zh.M_STONE_D),
        zh.box("SW_Body", (2.7, 0.42, 2.1), (0, 0, 1.33), zh.M_STONE),
        zh.box("SW_Cap", (2.95, 0.58, 0.22), (0, 0, 2.49), zh.M_STONE_D),
        zh.cyl("SW_Core", 0.52, 0.12, (0, -0.20, 1.35), zh.M_STONE_D, verts=28,
               rot=(PI / 2, 0, 0)),
    ]
    return zh.join(parts, "screen_wall")


def build_stele():
    """石碑: 须弥底座 + 圆首碑身 + 「永昌」红字 (面 -Y)。"""
    parts = [
        zh.box("ST_Base", (1.05, 0.5, 0.22), (0, 0, 0.11), zh.M_STONE_D),
        zh.box("ST_Body", (0.70, 0.20, 1.30), (0, 0, 0.87), zh.M_STONE),
        zh.cyl("ST_Head", 0.36, 0.20, (0, 0, 1.52), zh.M_STONE, verts=24,
               rot=(PI / 2, 0, 0)),
    ]
    t = zh.text_mesh("永昌", zh.M_TXT_R, 0.22, (0, -0.11, 1.02),
                     rot=(PI / 2, 0, 0), extrude=0.02)
    if t is not None:
        parts.append(t)
    return zh.join(parts, "stele")


def build_incense_burner():
    """青铜三足香炉: 炉身 + 三足 + 双耳 + 炉盖圆钮。"""
    parts = [
        zh.cyl("IB_Body", 0.30, 0.32, (0, 0, 0.54), zh.M_BRONZE, verts=18),
        zh.torus("IB_Lip", 0.30, 0.03, (0, 0, 0.70), zh.M_BRONZE),
        zh.cyl("IB_LegA", 0.045, 0.38, (0.20, 0, 0.19), zh.M_BRONZE, verts=8),
        zh.cyl("IB_LegB", 0.045, 0.38, (-0.10, 0.173, 0.19), zh.M_BRONZE, verts=8),
        zh.cyl("IB_LegC", 0.045, 0.38, (-0.10, -0.173, 0.19), zh.M_BRONZE, verts=8),
        zh.torus("IB_EarL", 0.08, 0.022, (-0.30, 0, 0.76), zh.M_BRONZE, rot=(0, PI / 2, 0)),
        zh.torus("IB_EarR", 0.08, 0.022, (0.30, 0, 0.76), zh.M_BRONZE, rot=(0, PI / 2, 0)),
        zh.cone("IB_Lid", 0.31, 0.10, (0, 0, 0.75), zh.M_BRONZE, verts=18, r_top=0.24),
        zh.sph("IB_Knob", 0.045, (0, 0, 0.83), zh.M_BRONZE, seg=10, ring=6),
    ]
    return zh.join(parts, "incense_burner")


def build_ba_xian_table():
    """八仙桌: 四腿 + 一周牙板 + 厚面板。桌高 0.85。"""
    parts = [
        zh.box("BT_Top", (1.02, 1.02, 0.07), (0, 0, 0.815), zh.M_LACQ),
    ]
    for sx in (-0.44, 0.44):
        for sy in (-0.44, 0.44):
            parts.append(zh.box(f"BT_Leg{sx}{sy}", (0.07, 0.07, 0.78),
                                (sx, sy, 0.39), zh.M_LACQ))
    parts += [
        zh.box("BT_ApronN", (0.90, 0.05, 0.14), (0, 0.44, 0.72), zh.M_LACQ),
        zh.box("BT_ApronS", (0.90, 0.05, 0.14), (0, -0.44, 0.72), zh.M_LACQ),
        zh.box("BT_ApronE", (0.05, 0.80, 0.14), (0.44, 0, 0.72), zh.M_LACQ),
        zh.box("BT_ApronW", (0.05, 0.80, 0.14), (-0.44, 0, 0.72), zh.M_LACQ),
    ]
    return zh.join(parts, "ba_xian_table")


def build_stool():
    """方凳: 四腿 + 望板 + 凳面。凳高 0.51。"""
    parts = [zh.box("SO_Top", (0.40, 0.40, 0.05), (0, 0, 0.485), zh.M_LACQ),
             zh.box("SO_Frame", (0.36, 0.36, 0.04), (0, 0, 0.44), zh.M_LACQ)]
    for sx in (-0.14, 0.14):
        for sy in (-0.14, 0.14):
            parts.append(zh.box(f"SO_Leg{sx}{sy}", (0.05, 0.05, 0.42),
                                (sx, sy, 0.21), zh.M_LACQ))
    return zh.join(parts, "stool")


def build_water_vat():
    """大水缸: 敛口陶缸 + 满水 + 石座 (太平缸, 兼防火)。"""
    parts = [
        zh.cone("WV_Body", 0.48, 0.85, (0, 0, 0.425), zh.M_JAR, verts=18, r_top=0.58),
        zh.torus("WV_Rim", 0.58, 0.035, (0, 0, 0.86), zh.M_JAR),
        zh.cyl("WV_Water", 0.50, 0.02, (0, 0, 0.78), zh.M_WATER, verts=18),
        zh.cyl("WV_Base", 0.52, 0.06, (0, 0, 0.03), zh.M_STONE_D, verts=18),
    ]
    return zh.join(parts, "water_vat")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # 注意: import build_chinese 会执行其模块底 main() 并缓存字体句柄,
    # 上面的场景重置会使其失效 (VectorFont removed) → 清缓存待懒重载
    zh.__dict__["_FONT"] = None
    zh.refresh_materials()
    extra_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("dashuifa", build_dashuifa),
        ("ruin_columns", build_ruin_columns),
        ("moon_gate", build_moon_gate),
        ("screen_wall", build_screen_wall),
        ("stele", build_stele),
        ("incense_burner", build_incense_burner),
        ("ba_xian_table", build_ba_xian_table),
        ("stool", build_stool),
        ("water_vat", build_water_vat),
    ]
    for name, fn in builders:
        zh.refresh_materials()  # delete_all 后重挂
        extra_materials()
        zh.delete_all()
        obj = fn()
        path = os.path.join(OUT, name + ".glb")
        filtered_gltf_export(
            path, export_format="GLB", export_yup=True, export_apply=False,
            export_materials="EXPORT", export_cameras=False, export_lights=False,
        )
        print("ZH2 ->", path, "verts=", len(obj.data.vertices))
    print("ZH2_DONE")


main()
