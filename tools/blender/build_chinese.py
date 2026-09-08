"""中式渐进式改编 Phase 1: 国营厂/人防主题 6 件 (LC 低模 + 做旧)。

文化映射 (对照现有三区, 渐进换皮):
  A SCP 安检大厅 -> 国营厂门卫/传达室   B 后室迷宫 -> 筒子楼楼道   C 工业核心 -> 锅炉房/人防
产出 assets/static/vendor/chinese/:
  lantern_red / stone_lion / roller_door / slogan_safety / slogan_tunnel / enamel_set
运行: blender --background --python tools/blender/build_chinese.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\simkai.ttf",
]
_FONT = None


def load_font():
    global _FONT
    if _FONT is not None:
        return _FONT
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                _FONT = bpy.data.fonts.load(p)
                print("ZH font ->", p)
                return _FONT
            except Exception as e:
                print("ZH font fail", p, e)
    print("ZH font: none found, slogans will be blank boards")
    return None


# ---------- 基础 ----------
def refresh_materials():
    """clear_scene 会清材质, 每个 builder 前重挂。"""
    g = globals()
    g["M_RED"] = make_material("M_ZH_Red", (0.72, 0.16, 0.09), rough=0.6)
    g["M_RED_GLOW"] = make_emissive("M_ZH_RedGlow", (0.82, 0.20, 0.10), 1.5)
    g["M_GOLD"] = make_material("M_ZH_Gold", (0.80, 0.64, 0.20), rough=0.35, metal=0.8)
    g["M_STONE"] = make_material("M_ZH_Stone", (0.56, 0.57, 0.53), rough=0.95)
    g["M_STONE_D"] = make_material("M_ZH_StoneDark", (0.44, 0.45, 0.42), rough=0.95)
    g["M_RUST"] = make_material("M_ZH_Rust", (0.48, 0.31, 0.20), rough=0.7, metal=0.3)
    g["M_STEEL"] = make_material("M_ZH_Steel", (0.34, 0.35, 0.37), rough=0.5, metal=0.6)
    g["M_BOARD_W"] = make_material("M_ZH_BoardWhite", (0.85, 0.83, 0.78), rough=0.8)
    g["M_TXT_R"] = make_material("M_ZH_TextRed", (0.66, 0.13, 0.09), rough=0.7)
    g["M_BOARD_R"] = make_material("M_ZH_BoardRed", (0.60, 0.13, 0.09), rough=0.8)
    g["M_TXT_W"] = make_material("M_ZH_TextWhite", (0.88, 0.86, 0.80), rough=0.7)
    g["M_ENAMEL"] = make_material("M_ZH_Enamel", (0.80, 0.83, 0.86), rough=0.25)
    g["M_EBLUE"] = make_material("M_ZH_EnamelBlue", (0.16, 0.32, 0.52), rough=0.3)
    g["M_THERMO"] = make_material("M_ZH_Thermo", (0.22, 0.42, 0.35), rough=0.4)
    g["M_ALU"] = make_material("M_ZH_Alu", (0.62, 0.63, 0.65), rough=0.3, metal=0.9)


def make_material(name, rgb, rough=0.7, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


def make_emissive(name, rgb, strength=1.0):
    m = make_material(name, rgb)
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Emission Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Emission Strength"].default_value = strength
    return m


def box(name, size, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    o.data.materials.append(mat)
    return o


def cyl(name, r, depth, loc, mat, verts=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts,
                                        location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return o


def sph(name, r, loc, mat, seg=16, ring=8, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=ring, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(mat)
    return o


def cone(name, r, depth, loc, mat, verts=12, rot=(0, 0, 0), r_top=0.0):
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r_top, depth=depth, vertices=verts,
                                    location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return o


def torus(name, major, minor, loc, mat, rot=(math.pi / 2, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return o


def text_mesh(txt, mat, size, loc, rot=(0, 0, 0), extrude=0.02):
    fc = load_font()
    if fc is None:
        return None
    bpy.ops.object.text_add(location=loc, rotation=rot)
    t = bpy.context.active_object
    t.data.body = txt
    t.data.font = fc
    t.data.size = size
    t.data.extrude = extrude
    t.data.align_x = "CENTER"
    t.data.align_y = "CENTER"
    t.data.space_character = 1.2
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.active_object
    o.data.materials.append(mat)
    return o


def join(parts, name):
    parts = [p for p in parts if p is not None]
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


def delete_all():
    # 只删对象, 不做 orphans_purge — purge 会把尚未被引用的 M_* 材质一并清掉
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()


# ---------- 构建 ----------
def build_lantern():
    """红灯笼: 红罩发光 + 金骨环 + 上下金盖 + 红穗。"""
    parts = [
        sph("Lantern_Globe", 0.30, (0, 0, 0.42), M_RED_GLOW, scale=(1, 1, 0.78)),
        torus("Lantern_RingLo", 0.235, 0.012, (0, 0, 0.31), M_GOLD),
        torus("Lantern_RingMid", 0.305, 0.012, (0, 0, 0.42), M_GOLD),
        torus("Lantern_RingHi", 0.235, 0.012, (0, 0, 0.53), M_GOLD),
        cyl("Lantern_CapT", 0.10, 0.06, (0, 0, 0.745), M_GOLD),
        torus("Lantern_Hook", 0.045, 0.012, (0, 0, 0.80), M_GOLD),
        cyl("Lantern_CapB", 0.10, 0.05, (0, 0, 0.095), M_GOLD),
        cyl("Lantern_TasselRod", 0.008, 0.10, (0, 0, 0.02), M_GOLD),
        cone("Lantern_Tassel", 0.05, 0.20, (0, 0, -0.13), M_RED, verts=8),
        sph("Lantern_Knot", 0.028, (0, 0, 0.075), M_GOLD, seg=8, ring=6),
    ]
    return join(parts, "lantern_red")


def build_stone_lion():
    """石狮子: 低模坐姿, 风化石灰岩。底座+身+鬃毛头+前腿+绣球。"""
    parts = [
        box("Lion_BaseLo", (0.92, 0.72, 0.26), (0, 0, 0.13), M_STONE_D),
        box("Lion_BaseHi", (0.76, 0.56, 0.14), (0, 0.02, 0.32), M_STONE),
        box("Lion_Body", (0.52, 0.86, 0.52), (0, 0.02, 0.65), M_STONE, rot=(-0.12, 0, 0)),
        box("Lion_Chest", (0.44, 0.30, 0.42), (0, -0.32, 0.88), M_STONE, rot=(-0.15, 0, 0)),
        box("Lion_Mane", (0.50, 0.50, 0.14), (0, -0.38, 1.10), M_STONE),
        box("Lion_Head", (0.40, 0.40, 0.36), (0, -0.44, 1.12), M_STONE),
        box("Lion_Snout", (0.24, 0.14, 0.14), (0, -0.60, 1.04), M_STONE),
        cone("Lion_EarL", 0.05, 0.10, (-0.16, -0.42, 1.32), M_STONE_D, rot=(math.pi / 2, 0, 0)),
        cone("Lion_EarR", 0.05, 0.10, (0.16, -0.42, 1.32), M_STONE_D, rot=(math.pi / 2, 0, 0)),
        box("Lion_LegL", (0.14, 0.16, 0.50), (-0.17, -0.34, 0.55), M_STONE),
        box("Lion_LegR", (0.14, 0.16, 0.50), (0.17, -0.34, 0.55), M_STONE),
        box("Lion_PawL", (0.18, 0.22, 0.09), (-0.17, -0.38, 0.40), M_STONE),
        box("Lion_PawR", (0.18, 0.22, 0.09), (0.17, -0.38, 0.40), M_STONE),
        box("Lion_HaunchL", (0.20, 0.34, 0.40), (-0.17, 0.24, 0.72), M_STONE),
        box("Lion_HaunchR", (0.20, 0.34, 0.40), (0.17, 0.24, 0.72), M_STONE),
        box("Lion_TailA", (0.08, 0.30, 0.08), (0, 0.44, 0.90), M_STONE, rot=(0.5, 0, 0)),
        box("Lion_TailB", (0.08, 0.08, 0.22), (0, 0.38, 1.10), M_STONE),
        sph("Lion_Ball", 0.115, (0, -0.52, 0.51), M_STONE_D, seg=10, ring=6),
    ]
    return join(parts, "stone_lion")


def build_roller_door():
    """卷帘门: 4m 墙模块 (4 宽×1 厚×4 高), 锈橙门板+钢导轨+顶盒。装饰面朝 -Y。"""
    parts = [
        box("Roller_RailL", (0.14, 0.20, 3.8), (-1.90, 0, 1.90), M_STEEL),
        box("Roller_RailR", (0.14, 0.20, 3.8), (1.90, 0, 1.90), M_STEEL),
        box("Roller_Housing", (3.94, 0.52, 0.46), (0, 0.02, 3.76), M_RUST),
        box("Roller_Lock", (0.18, 0.10, 0.28), (0, -0.10, 0.30), M_STEEL),
    ]
    for i in range(7):
        z = 0.28 + i * 0.47
        parts.append(box(f"Roller_Slat{i}", (3.62, 0.07, 0.40),
                         (0, (-0.02 if i % 2 else 0.02), z), M_RUST))
    parts.append(box("Roller_BottomBar", (3.62, 0.12, 0.12), (0, -0.03, 0.08), M_STEEL))
    return join(parts, "roller_door")


def _slogan_board(base_mat, text_mat, txt, name):
    parts = [
        box("S_Board", (3.80, 0.09, 1.10), (0, 0, 1.42), base_mat),
        box("S_LegL", (0.10, 0.10, 1.42), (-1.62, 0, 0.71), M_STEEL),
        box("S_LegR", (0.10, 0.10, 1.42), (1.62, 0, 0.71), M_STEEL),
        box("S_BraceL", (0.08, 0.40, 0.08), (-1.62, 0.16, 1.05), M_STEEL, rot=(0.6, 0, 0)),
        box("S_BraceR", (0.08, 0.40, 0.08), (1.62, 0.16, 1.05), M_STEEL, rot=(0.6, 0, 0)),
        box("S_CapL", (0.16, 0.16, 0.06), (-1.62, 0, 1.44), M_STEEL),
        box("S_CapR", (0.16, 0.16, 0.06), (1.62, 0, 1.44), M_STEEL),
    ]
    # 文字贴板正面 (-Y 面): rot_x=90° 立起后字面即朝 -Y, 阅读向 +X (观察者右手侧), 不加 Z 旋转
    txt_obj = text_mesh(txt, text_mat, 0.42, (0, -0.09, 1.42),
                        rot=(math.pi / 2, 0, 0), extrude=0.025)
    if txt_obj is not None:
        parts.append(txt_obj)
    return join(parts, name)


def build_slogan_safety():
    return _slogan_board(M_BOARD_W, M_TXT_R, "安全生产  人人有责", "slogan_safety")


def build_slogan_tunnel():
    return _slogan_board(M_BOARD_R, M_TXT_W, "深挖洞  广积粮", "slogan_tunnel")


def build_enamel_set():
    """搪瓷缸 + 暖水瓶 (桌面道具)。"""
    parts = [
        # 搪瓷缸
        cyl("Mug_Body", 0.055, 0.11, (0.22, 0, 0.055), M_ENAMEL),
        torus("Mug_Rim", 0.055, 0.012, (0.22, 0, 0.11), M_EBLUE),
        torus("Mug_Band", 0.0575, 0.008, (0.22, 0, 0.085), M_EBLUE),
        box("Mug_HandleA", (0.012, 0.012, 0.035), (0.155, 0, 0.085), M_ENAMEL),
        box("Mug_HandleB", (0.012, 0.012, 0.035), (0.155, 0, 0.035), M_ENAMEL),
        box("Mug_HandleC", (0.012, 0.045, 0.012), (0.155, 0, 0.06), M_ENAMEL),
        # 暖水瓶
        cone("Thermo_Shell", 0.085, 0.34, (0, 0, 0.17), M_THERMO, verts=14, rot=(0, 0, 0), r_top=0.028),
        cyl("Thermo_Base", 0.088, 0.035, (0, 0, 0.018), M_ALU),
        cyl("Thermo_Cap", 0.052, 0.055, (0, 0, 0.352), M_ALU),
        box("Thermo_Spout", (0.045, 0.075, 0.055), (0, -0.07, 0.33), M_ALU, rot=(0.35, 0, 0)),
        torus("Thermo_Band", 0.062, 0.010, (0, 0, 0.275), M_ALU),
    ]
    return join(parts, "enamel_set")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    refresh_materials()
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("lantern_red", build_lantern),
        ("stone_lion", build_stone_lion),
        ("roller_door", build_roller_door),
        ("slogan_safety", build_slogan_safety),
        ("slogan_tunnel", build_slogan_tunnel),
        ("enamel_set", build_enamel_set),
    ]
    for name, fn in builders:
        refresh_materials()  # 防 delete_all 后材质失效
        delete_all()
        obj = fn()
        path = os.path.join(OUT, name + ".glb")
        filtered_gltf_export(
            path, export_format="GLB", export_yup=True, export_apply=False,
            export_materials="EXPORT", export_cameras=False, export_lights=False,
        )
        print("ZH ->", path, "verts=", len(obj.data.vertices))
    print("ZH_DONE")


main()
