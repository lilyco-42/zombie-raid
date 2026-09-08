"""
Lethal-Company 风格资产程序化生成器 (Blender headless)

用法:
    blender -b --python tools/blender/build_lc_assets.py

产出:
    assets/static/kit_industrial.glb     静态关卡模块件
    assets/dynamic/monster_zombie.glb    动态怪物(带骨架 + idle/walk 动作)
    assets/_src/*.blend                  Blender 源文件

约定:
    * 只新增文件，不修改/删除项目里任何已有资产
    * Blender +Y 为前 => 导出 glTF(convert Y-up) 后在 Godot 中为 -Z 前，符合 Godot 朝向约定
    * 命名: SM_ = Static Mesh(静态网格), SK_ = Skeletal(带骨架), M_ = Material
"""

import os
import sys
import math
import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(ROOT, "assets", "static")
DYN_DIR = os.path.join(ROOT, "assets", "dynamic")
SRC_DIR = os.path.join(ROOT, "assets", "_src")

for d in (STATIC_DIR, DYN_DIR, SRC_DIR):
    os.makedirs(d, exist_ok=True)


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_material(name, color, rough=0.85, metal=0.05):
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
    return mat


def make_emissive(name, color, strength=4.0):
    """自发光材质 (用于灯带、屏幕、防爆门红光条)。"""
    mat = bpy.data.materials.get(name)
    if mat:
        return mat
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def box(name, loc, size, mat=None):
    """创建一个轴对齐盒子并应用缩放。loc/size 为 (x, y, z)。"""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 0.0))
    ob = bpy.context.object
    ob.name = name
    ob.data.name = name + "_Mesh"
    ob.scale = size
    ob.location = loc
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        ob.data.materials.append(mat)
    return ob


def add_verts_to_group(ob, group_name):
    g = ob.vertex_groups.get(group_name) or ob.vertex_groups.new(name=group_name)
    idx = [v.index for v in ob.data.vertices]
    g.add(idx, 1.0, "REPLACE")


def join_objects(objects, name):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = name
    joined.data.name = name + "_Mesh"
    return joined


def filtered_gltf_export(filepath, **kwargs):
    """只传入当前 Blender 版本支持的 glTF 导出参数。"""
    props = bpy.ops.export_scene.gltf.get_rna_type().properties
    safe = {k: v for k, v in kwargs.items() if k in props}
    return bpy.ops.export_scene.gltf(filepath=filepath, **safe)


# --------------------------------------------------------------------------
# 1. 静态资源: 工业关卡模块件 (Static Mesh Kit)
# --------------------------------------------------------------------------
def build_static_kit():
    clear_scene()

    m_concrete = make_material("M_Concrete", (0.32, 0.31, 0.29), 0.95, 0.0)
    m_metal = make_material("M_Metal_Rust", (0.34, 0.22, 0.16), 0.7, 0.6)
    m_steel = make_material("M_Steel_Dark", (0.15, 0.15, 0.17), 0.5, 0.8)
    m_hazard = make_material("M_Hazard", (0.62, 0.52, 0.10), 0.6, 0.2)

    parts = []

    # 地板 4x4
    parts.append(box("SM_Floor_4x4", (0, 0, -0.1), (4, 4, 0.2), m_concrete))
    # 天花板 4x4
    parts.append(box("SM_Ceiling_4x4", (0, 0, 3.1), (4, 4, 0.2), m_concrete))

    # 实心墙 4x3
    parts.append(box("SM_Wall_4x3", (0, -0.1, 1.5), (4, 0.2, 3.0), m_concrete))

    # 带门洞墙 4x3 (门洞 1.4w x 2.2h)
    dw, dh = 1.4, 2.2
    side = (4 - dw) / 2
    parts.append(box("SM_Wall_Door_4x3_A", (-(dw / 2 + side / 2), -0.1, 1.5), (side, 0.2, 3.0), m_concrete))
    parts.append(box("SM_Wall_Door_4x3_B", (+(dw / 2 + side / 2), -0.1, 1.5), (side, 0.2, 3.0), m_concrete))
    parts.append(box("SM_Wall_Door_4x3_C", (0, -0.1, dh + (3.0 - dh) / 2), (dw, 0.2, 3.0 - dh), m_concrete))

    # 门框
    parts.append(box("SM_DoorFrame_L", (-0.8, -0.1, 1.1), (0.15, 0.3, 2.2), m_steel))
    parts.append(box("SM_DoorFrame_R", (0.8, -0.1, 1.1), (0.15, 0.3, 2.2), m_steel))
    parts.append(box("SM_DoorFrame_T", (0, -0.1, 2.25), (1.75, 0.3, 0.15), m_steel))

    # 楼梯 (4 长 x 1.2 宽 x 3 高, 8 级)
    stair_parts = []
    steps = 8
    for i in range(steps):
        z = (i + 0.5) * (3.0 / steps)
        y = -(1.8 - (i + 0.5) * (3.6 / steps))
        stair_parts.append(box("SM_Stair_Step_%02d" % i, (0, y, z), (1.6, 0.52, 0.18), m_steel))
    parts += stair_parts

    # 管道 4m
    parts.append(box("SM_Pipe_4m", (0, 0, 2.85), (4.0, 0.22, 0.22), m_metal))
    # 货架 2x2
    shelf = []
    for i in range(3):
        shelf.append(box("SM_Shelf_Plane_%d" % i, (0, 0, 0.6 + i * 0.8), (2.0, 0.6, 0.06), m_steel))
    for sx in (-0.95, 0.95):
        for sy in (-0.25, 0.25):
            shelf.append(box("SM_Shelf_Post", (sx, sy, 1.1), (0.08, 0.08, 2.2), m_steel))
    parts += shelf

    # 集装箱 6x2.4x2.4
    parts.append(box("SM_Container_6m", (0, 0, 1.2), (6.0, 2.4, 2.4), m_metal))
    # 板条箱
    parts.append(box("SM_Crate_1m", (0, 0, 0.5), (1.0, 1.0, 1.0), m_hazard))
    # 铁桶
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=0.9, location=(0, 0, 0.45))
    barrel = bpy.context.object
    barrel.name = "SM_Barrel"
    barrel.data.materials.append(m_metal)
    parts.append(barrel)

    # 栏杆 4m
    rail = []
    rail.append(box("SM_Railing_Top", (0, 0, 1.1), (4.0, 0.06, 0.06), m_steel))
    rail.append(box("SM_Railing_Mid", (0, 0, 0.7), (4.0, 0.05, 0.05), m_steel))
    for i in range(5):
        rail.append(box("SM_Railing_Post_%d" % i, (-1.8 + i * 0.9, 0, 0.55), (0.07, 0.07, 1.1), m_steel))
    parts += rail

    # ---- LC 风格设施 (transformative derivative: 自有配色 + 自有比例) ----
    m_red = make_emissive("M_LC_RedLight", (1.0, 0.12, 0.10), 5.0)
    m_blue = make_emissive("M_LC_BlueLight", (0.30, 0.70, 1.0), 4.0)
    m_panel = make_material("M_LC_Panel", (0.38, 0.40, 0.42), 0.6, 0.5)
    m_screen = make_material("M_LC_Screen", (0.05, 0.08, 0.10), 0.3, 0.2)

    # 长条吊顶灯 (4m, 蓝白光)
    parts.append(box("SM_LC_LightStrip", (0, 0, 2.95), (3.6, 0.18, 0.06), m_blue))
    # 通风口 2x2 (地板)
    parts.append(box("SM_LC_VentGrate", (0, 0, 0.01), (1.6, 1.6, 0.05), m_steel))
    # 防爆门 (4x3, 顶部红光条)
    parts.append(box("SM_LC_BlastDoor", (0, -0.05, 1.5), (3.6, 0.18, 2.8), m_steel))
    parts.append(box("SM_LC_BlastLight", (0, -0.12, 2.85), (3.4, 0.05, 0.10), m_red))
    # 墙上终端 (小电脑 + 暗屏)
    parts.append(box("SM_LC_Terminal", (0, 0, 1.2), (0.9, 0.25, 1.0), m_panel))
    parts.append(box("SM_LC_TerminalScreen", (0, 0.14, 1.4), (0.7, 0.04, 0.55), m_screen))

    # ---- LC 风格安防 / 设施模块 (transformative derivative: 自有比例 + 自有配色) ----
    # 监控摄像头（壁装球头 + 红色待机灯）
    _cam = []
    _cam.append(box("SM_LC_Camera_Plate", (0, 0, 0.02), (0.30, 0.22, 0.05), m_steel))
    _cam.append(_cyl("SM_LC_Camera_Arm", (0, 0.10, 0.05), 0.025, 0.20, m_steel, (math.pi / 2, 0, 0)))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(0, 0.18, 0.10))
    _ch = bpy.context.object
    _ch.name = "SM_LC_Camera_Head"
    _ch.data.name = "SM_LC_Camera_Head_Mesh"
    _ch.data.materials.append(m_steel)
    _cam.append(_ch)
    _cam.append(box("SM_LC_Camera_Led", (0, 0.18, 0.20), (0.03, 0.03, 0.03), m_red))
    parts.append(join_objects(_cam, "SM_LC_Camera"))

    # 门禁闸机（双立柱 + 横杆 + 黄黑摆动臂）
    _ts = []
    _ts.append(box("SM_LC_Turnstile_PostL", (-0.45, 0, 0.5), (0.12, 0.12, 1.0), m_steel))
    _ts.append(box("SM_LC_Turnstile_PostR", (0.45, 0, 0.5), (0.12, 0.12, 1.0), m_steel))
    _ts.append(box("SM_LC_Turnstile_Top", (0, 0, 1.0), (1.10, 0.08, 0.10), m_steel))
    _ts.append(box("SM_LC_Turnstile_Arm", (0, 0.28, 0.55), (0.90, 0.05, 0.04), m_hazard))
    parts.append(join_objects(_ts, "SM_LC_Turnstile"))

    # 警报器（底座 + 旋转红蓝灯罩）
    _sr = []
    _sr.append(_cyl("SM_LC_Siren_Base", (0, 0, 0.05), 0.12, 0.10, m_steel))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.14, location=(0, 0, 0.20))
    _sd = bpy.context.object
    _sd.name = "SM_LC_Siren_Dome"
    _sd.data.name = "SM_LC_Siren_Dome_Mesh"
    _sd.data.materials.append(m_red)
    _sr.append(_sd)
    _sr.append(box("SM_LC_Siren_Top", (0, 0, 0.32), (0.08, 0.08, 0.06), m_blue))
    parts.append(join_objects(_sr, "SM_LC_Siren"))

    # 员工储物柜（4 格排柜）
    _lk = []
    _lk.append(box("SM_LC_Locker_Body", (0, 0, 1.0), (2.0, 0.5, 2.0), m_panel))
    for i in range(4):
        _x = -0.75 + i * 0.5
        _lk.append(box("SM_LC_Locker_Door_%d" % i, (_x, 0.26, 1.0), (0.44, 0.02, 1.9), m_steel))
        _lk.append(box("SM_LC_Locker_Handle_%d" % i, (_x + 0.16, 0.28, 0.55), (0.03, 0.02, 0.18), m_steel))
    parts.append(join_objects(_lk, "SM_LC_Locker"))

    # 监控屏墙（多屏 + 暗底）
    _mw = []
    _mw.append(box("SM_LC_MonitorWall_Back", (0, 0, 1.2), (2.4, 0.1, 1.6), m_panel))
    for i in range(4):
        _col = i % 2
        _row = i // 2
        _x = -0.55 + _col * 1.1
        _z = 0.85 + _row * 0.8
        _mw.append(box("SM_LC_Monitor_%d" % i, (_x, 0.06, _z), (0.95, 0.04, 0.7), m_blue))
    parts.append(join_objects(_mw, "SM_LC_MonitorWall"))

    # ---- 第七轮: LC 设施杂项 / 环境道具 (transformative derivative: 自有比例 + 自有配色) ----
    m_redbox = make_material("M_LC_RedBox", (0.78, 0.16, 0.14), 0.55, 0.2)
    m_greenled = make_emissive("M_LC_GreenLed", (0.20, 0.85, 0.35), 4.0)
    m_wood = make_material("M_LC_Wood", (0.45, 0.32, 0.18), 0.95, 0.0)

    # 门禁刷卡机（壁挂小机 + 暗屏 + 绿待机灯）
    _cr = []
    _cr.append(box("SM_LC_CardReader_Back", (0, 0, 0.15), (0.22, 0.16, 0.30), m_panel))
    _cr.append(box("SM_LC_CardReader_Screen", (0, 0.02, 0.20), (0.16, 0.03, 0.16), m_screen))
    _cr.append(box("SM_LC_CardReader_Slot", (0, 0.02, 0.10), (0.14, 0.02, 0.02), m_steel))
    _cr.append(box("SM_LC_CardReader_Led", (0.07, 0.02, 0.27), (0.025, 0.02, 0.025), m_greenled))
    parts.append(join_objects(_cr, "SM_LC_CardReader"))

    # 灭火器（红罐 + 黑阀 + 喷嘴）
    _fe = []
    _fe.append(_cyl("SM_LC_FireExt_Body", (0, 0, 0.28), 0.085, 0.50, m_redbox))
    _fe.append(_cyl("SM_LC_FireExt_Top", (0, 0, 0.56), 0.05, 0.08, m_steel))
    _fe.append(box("SM_LC_FireExt_Nozzle", (0.05, 0, 0.60), (0.10, 0.05, 0.05), m_steel))
    parts.append(join_objects(_fe, "SM_LC_FireExtinguisher"))

    # 配电箱（背板 + 门 + 把手 + 警示块）
    _eb = []
    _eb.append(box("SM_LC_ElecBox_Back", (0, 0, 0.40), (0.50, 0.12, 0.70), m_panel))
    _eb.append(box("SM_LC_ElecBox_Door", (0, 0.07, 0.40), (0.46, 0.03, 0.62), m_steel))
    _eb.append(box("SM_LC_ElecBox_Handle", (0.14, 0.09, 0.40), (0.04, 0.02, 0.18), m_steel))
    _eb.append(box("SM_LC_ElecBox_Warn", (0, 0.09, 0.62), (0.10, 0.02, 0.10), m_redbox))
    parts.append(join_objects(_eb, "SM_LC_ElectricBox"))

    # 通风管道弯头（L 形，钢制）
    _vb = []
    _vb.append(box("SM_LC_VentBend_H", (0.20, 0, 0.40), (0.80, 0.40, 0.40), m_steel))
    _vb.append(box("SM_LC_VentBend_V", (0.60, 0, 0.20), (0.40, 0.40, 0.80), m_steel))
    parts.append(join_objects(_vb, "SM_LC_VentBend"))

    # 警示栏（红白条横板 + 双腿）
    _bc = []
    _bc.append(box("SM_LC_Barricade_Board", (0, 0, 0.55), (1.20, 0.10, 0.30), m_hazard))
    _bc.append(box("SM_LC_Barricade_LegL", (-0.50, 0, 0.25), (0.06, 0.06, 0.50), m_steel))
    _bc.append(box("SM_LC_Barricade_LegR", (0.50, 0, 0.25), (0.06, 0.06, 0.50), m_steel))
    parts.append(join_objects(_bc, "SM_LC_Barricade"))

    # 货运托盘 + 货箱（木托盘 + 金属集装箱块）
    _pl = []
    _pl.append(box("SM_LC_Pallet_Base", (0, 0, 0.06), (1.0, 0.10, 1.0), m_wood))
    for i, sx in enumerate((-0.40, 0.0, 0.40)):
        _pl.append(box("SM_LC_Pallet_Slat_%d" % i, (sx, 0, 0.14), (0.12, 0.80, 0.04), m_wood))
    _pl.append(box("SM_LC_Pallet_Crate", (0, 0, 0.55), (0.80, 0.70, 0.80), m_metal))
    parts.append(join_objects(_pl, "SM_LC_Pallet"))

    # 把所有静态件收进一个集合，方便 Godot 侧识别
    kit_col = bpy.data.collections.new("Kit_Industrial")
    bpy.context.scene.collection.children.link(kit_col)
    for ob in parts:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        kit_col.objects.link(ob)

    # 源 + 导出
    blend_path = os.path.join(SRC_DIR, "kit_industrial.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    glb_path = os.path.join(STATIC_DIR, "kit_industrial.glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("STATIC_KIT ->", glb_path)
    return glb_path


# --------------------------------------------------------------------------
# 2. 动态资源: 僵尸怪物 (骨架 + idle / walk)
# --------------------------------------------------------------------------
BONES = [
    # name,        head,              tail,               parent
    ("root",      (0.0, 0.0, 0.00),  (0.0, 0.0, 0.20),   None),
    ("pelvis",    (0.0, 0.0, 0.95),  (0.0, 0.0, 1.15),   "root"),
    ("spine",     (0.0, 0.0, 1.15),  (0.0, 0.05, 1.50),  "pelvis"),
    ("head",      (0.0, 0.05, 1.50), (0.0, 0.10, 1.85),  "spine"),
    ("arm_up.L",  (0.20, 0.0, 1.50), (0.20, 0.0, 1.20),  "spine"),
    ("arm_lo.L",  (0.20, 0.0, 1.20), (0.20, 0.0, 0.90),  "arm_up.L"),
    ("arm_up.R",  (-0.20, 0.0, 1.50), (-0.20, 0.0, 1.20), "spine"),
    ("arm_lo.R",  (-0.20, 0.0, 1.20), (-0.20, 0.0, 0.90), "arm_up.R"),
    ("leg_up.L",  (0.11, 0.0, 0.95), (0.11, 0.0, 0.50),  "pelvis"),
    ("leg_lo.L",  (0.11, 0.0, 0.50), (0.11, 0.0, 0.08),  "leg_up.L"),
    ("leg_up.R",  (-0.11, 0.0, 0.95), (-0.11, 0.0, 0.50), "pelvis"),
    ("leg_lo.R",  (-0.11, 0.0, 0.50), (-0.11, 0.0, 0.08), "leg_up.R"),
]

# 部件: 名字, 位置, 尺寸, 绑定骨骼
ZOMBIE_PARTS = [
    ("pelvis",   (0.0, 0.00, 1.02), (0.34, 0.24, 0.26), "pelvis"),
    ("torso",    (0.0, 0.03, 1.33), (0.44, 0.27, 0.48), "spine"),
    ("head",     (0.0, 0.07, 1.68), (0.25, 0.25, 0.29), "head"),
    ("jaw",      (0.0, 0.13, 1.57), (0.20, 0.14, 0.09), "head"),
    ("arm_up.L", (0.20, 0.0, 1.35), (0.13, 0.13, 0.34), "arm_up.L"),
    ("arm_lo.L", (0.20, 0.02, 1.05), (0.12, 0.12, 0.34), "arm_lo.L"),
    ("arm_up.R", (-0.20, 0.0, 1.35), (0.13, 0.13, 0.34), "arm_up.R"),
    ("arm_lo.R", (-0.20, 0.02, 1.05), (0.12, 0.12, 0.34), "arm_lo.R"),
    ("leg_up.L", (0.11, 0.0, 0.72), (0.16, 0.17, 0.46), "leg_up.L"),
    ("leg_lo.L", (0.11, 0.0, 0.29), (0.14, 0.15, 0.44), "leg_lo.L"),
    ("foot.L",   (0.11, 0.06, 0.045), (0.15, 0.27, 0.10), "leg_lo.L"),
    ("leg_up.R", (-0.11, 0.0, 0.72), (0.16, 0.17, 0.46), "leg_up.R"),
    ("leg_lo.R", (-0.11, 0.0, 0.29), (0.14, 0.15, 0.44), "leg_lo.R"),
    ("foot.R",   (-0.11, 0.06, 0.045), (0.15, 0.27, 0.10), "leg_lo.R"),
]

# 潜行怪物 (transformative derivative: 仿致命公司 Bracken 但自有比例/姿态/配色)
BONES_BRACKEN = [
    # name,        head,              tail,               parent
    ("root",      (0.0, 0.0, 0.00),  (0.0, 0.0, 0.15),   None),
    ("pelvis",    (0.0, 0.0, 0.55),  (0.0, 0.0, 0.70),   "root"),
    ("spine",     (0.0, 0.05, 0.70), (0.10, 0.05, 0.95),  "pelvis"),  # 前倾
    ("head",      (0.15, 0.05, 0.95), (0.25, 0.08, 1.20),  "spine"),  # 头前探
    ("arm_up.L",  (0.15, 0.0, 0.90), (0.15, 0.0, 0.55),  "spine"),
    ("arm_lo.L",  (0.15, 0.0, 0.55), (0.15, 0.0, 0.10),  "arm_up.L"),
    ("arm_up.R",  (-0.15, 0.0, 0.90), (-0.15, 0.0, 0.55), "spine"),
    ("arm_lo.R",  (-0.15, 0.0, 0.55), (-0.15, 0.0, 0.10), "arm_up.R"),
    ("leg_up.L",  (0.11, 0.0, 0.55), (0.11, 0.0, 0.22),  "pelvis"),
    ("leg_lo.L",  (0.11, 0.0, 0.22), (0.11, 0.0, 0.04),  "leg_up.L"),
    ("leg_up.R",  (-0.11, 0.0, 0.55), (-0.11, 0.0, 0.22), "pelvis"),
    ("leg_lo.R",  (-0.11, 0.0, 0.22), (-0.11, 0.0, 0.04), "leg_up.R"),
]

BRACKEN_PARTS = [
    ("pelvis",   (0.0, 0.00, 0.62), (0.32, 0.24, 0.22), "pelvis"),
    ("torso",    (0.08, 0.03, 0.82), (0.42, 0.26, 0.36), "spine"),
    ("head",     (0.20, 0.07, 1.05), (0.22, 0.22, 0.26), "head"),
    ("jaw",      (0.25, 0.12, 0.95), (0.18, 0.13, 0.08), "head"),
    ("arm_up.L", (0.15, 0.0, 0.72), (0.12, 0.12, 0.36), "arm_up.L"),
    ("arm_lo.L", (0.15, 0.02, 0.32), (0.11, 0.11, 0.42), "arm_lo.L"),
    ("arm_up.R", (-0.15, 0.0, 0.72), (0.12, 0.12, 0.36), "arm_up.R"),
    ("arm_lo.R", (-0.15, 0.02, 0.32), (0.11, 0.11, 0.42), "arm_lo.R"),
    ("leg_up.L", (0.11, 0.0, 0.38), (0.15, 0.16, 0.34), "leg_up.L"),
    ("leg_lo.L", (0.11, 0.0, 0.13), (0.13, 0.14, 0.24), "leg_lo.L"),
    ("foot.L",   (0.11, 0.06, 0.03), (0.14, 0.24, 0.06), "leg_lo.L"),
    ("leg_up.R", (-0.11, 0.0, 0.38), (0.15, 0.16, 0.34), "leg_up.R"),
    ("leg_lo.R", (-0.11, 0.0, 0.13), (0.13, 0.14, 0.24), "leg_lo.R"),
    ("foot.R",   (-0.11, 0.06, 0.03), (0.14, 0.24, 0.06), "leg_lo.R"),
]

# 线圈头怪物 (仿致命公司 Coil-Head, transformative derivative: 直立 + 无脸方头 + 头顶可转)
# 复用 BONES (僵尸骨架, 直立姿态)
COIL_PARTS = [
    ("pelvis",      (0.0, 0.00, 1.02),  (0.34, 0.24, 0.26), "pelvis"),
    ("torso",       (0.0, 0.03, 1.33),  (0.44, 0.27, 0.48), "spine"),
    ("neck_spring", (0.0, 0.03, 1.72),  (0.08, 0.08, 0.32), "head"),  # 细高弹簧颈
    ("coil_head",   (0.0, 0.05, 1.97),  (0.28, 0.28, 0.18), "head"),  # 方块线圈头
    ("arm_up.L",    (0.20, 0.0, 1.35),  (0.13, 0.13, 0.34), "arm_up.L"),
    ("arm_lo.L",    (0.20, 0.02, 1.05), (0.12, 0.12, 0.34), "arm_lo.L"),
    ("arm_up.R",    (-0.20, 0.0, 1.35), (0.13, 0.13, 0.34), "arm_up.R"),
    ("arm_lo.R",    (-0.20, 0.02, 1.05),(0.12, 0.12, 0.34), "arm_lo.R"),
    ("leg_up.L",    (0.11, 0.0, 0.72),  (0.16, 0.17, 0.46), "leg_up.L"),
    ("leg_lo.L",    (0.11, 0.0, 0.29),  (0.14, 0.15, 0.44), "leg_lo.L"),
    ("foot.L",      (0.11, 0.06, 0.045),(0.15, 0.27, 0.10), "leg_lo.L"),
    ("leg_up.R",    (-0.11, 0.0, 0.72), (0.16, 0.17, 0.46), "leg_up.R"),
    ("leg_lo.R",    (-0.11, 0.0, 0.29), (0.14, 0.15, 0.44), "leg_lo.R"),
    ("foot.R",      (-0.11, 0.06, 0.045),(0.15, 0.27, 0.10), "leg_lo.R"),
]


def build_armature(bones=BONES, name="SK_Zombie_Armature"):
    arm = bpy.data.armatures.new(name)
    arm_obj = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for bone_name, head, tail, parent in bones:
        eb = arm.edit_bones.new(bone_name)
        eb.head = head
        eb.tail = tail
        if parent:
            eb.parent = arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def build_animation(arm_obj, name, frame_end, tracks):
    """tracks: {bone: (frames, values, data_path, index)}

    使用高层 keyframe_insert API 写关键帧，兼容 Blender 4.4+ 的分层动画系统。
    """
    try:
        bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    except Exception:
        pass

    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    arm_obj.animation_data.action = action

    scene = bpy.context.scene
    all_frames = sorted({f for (frames, _v, _dp, _i) in tracks.values() for f in frames})

    for bone_name in tracks:
        arm_obj.pose.bones[bone_name].rotation_mode = "XYZ"

    for f in all_frames:
        scene.frame_set(f)
        for bone_name, (frames, values, dp, idx) in tracks.items():
            if f not in frames:
                continue
            v = values[list(frames).index(f)]
            pbone = arm_obj.pose.bones[bone_name]
            if dp == "rotation_euler":
                euler = [0.0, 0.0, 0.0]
                euler[idx] = v
                pbone.rotation_euler = tuple(euler)
                pbone.keyframe_insert(data_path="rotation_euler", frame=f)
            else:
                loc = [0.0, 0.0, 0.0]
                loc[idx] = v
                pbone.location = tuple(loc)
                pbone.keyframe_insert(data_path="location", frame=f)

    action.frame_start = 1
    action.frame_end = frame_end
    scene.frame_set(1)
    return action


def build_zombie():
    clear_scene()
    scene = bpy.context.scene
    scene.render.fps = 24

    m_skin = make_material("M_Zombie_Skin", (0.29, 0.34, 0.24), 0.9, 0.0)
    m_cloth = make_material("M_Zombie_Cloth", (0.20, 0.20, 0.23), 0.95, 0.0)

    arm_obj = build_armature()

    # --- 网格部件 ---
    mesh_parts = []
    for i, (pname, loc, size, bone_name) in enumerate(ZOMBIE_PARTS):
        mat = m_cloth if pname.startswith(("torso", "pelvis", "leg_up", "leg_lo")) else m_skin
        ob = box("SK_Zombie_" + pname, loc, size, mat)
        add_verts_to_group(ob, bone_name)
        mesh_parts.append(ob)

    body = join_objects(mesh_parts, "SK_Zombie_Body")

    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj
    body.parent = arm_obj
    body.matrix_parent_inverse = arm_obj.matrix_world.inverted()

    # --- 动作: walk (1..25, 首尾同值可无缝循环) ---
    f = [1, 7, 13, 19, 25]
    arm_base = 1.15  # 僵尸前伸手臂
    walk_tracks = {
        "leg_up.L": (f, [0.45, 0.0, -0.40, 0.0, 0.45], "rotation_euler", 0),
        "leg_up.R": (f, [-0.40, 0.0, 0.45, 0.0, -0.40], "rotation_euler", 0),
        "leg_lo.L": (f, [-0.08, -0.55, -0.18, -0.06, -0.08], "rotation_euler", 0),
        "leg_lo.R": (f, [-0.18, -0.06, -0.08, -0.55, -0.18], "rotation_euler", 0),
        "arm_up.L": (f, [arm_base - 0.12, arm_base, arm_base + 0.12, arm_base, arm_base - 0.12], "rotation_euler", 0),
        "arm_up.R": (f, [arm_base + 0.12, arm_base, arm_base - 0.12, arm_base, arm_base + 0.12], "rotation_euler", 0),
        "arm_lo.L": (f, [-0.35, -0.45, -0.35, -0.30, -0.35], "rotation_euler", 0),
        "arm_lo.R": (f, [-0.35, -0.30, -0.35, -0.45, -0.35], "rotation_euler", 0),
        "pelvis":   (f, [0.015, 0.05, 0.015, 0.05, 0.015], "location", 2),
        "spine":    (f, [0.06, 0.03, 0.06, 0.03, 0.06], "rotation_euler", 0),
    }
    build_animation(arm_obj, "walk", 25, walk_tracks)

    # --- 动作: idle (呼吸 + 轻微摇晃) ---
    fi = [1, 16, 31, 49]
    idle_tracks = {
        "spine":    (fi, [0.05, 0.09, 0.05, 0.05], "rotation_euler", 0),
        "head":     (fi, [0.0, 0.10, 0.0, 0.0], "rotation_euler", 0),
        "arm_up.L": (fi, [arm_base - 0.05, arm_base + 0.06, arm_base - 0.02, arm_base - 0.05], "rotation_euler", 0),
        "arm_up.R": (fi, [arm_base - 0.05, arm_base + 0.06, arm_base - 0.02, arm_base - 0.05], "rotation_euler", 0),
        "pelvis":   (fi, [0.0, 0.02, 0.0, 0.0], "location", 2),
    }
    build_animation(arm_obj, "idle", 48, idle_tracks)

    # --- 源 + 导出 ---
    blend_path = os.path.join(SRC_DIR, "monster_zombie.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    glb_path = os.path.join(DYN_DIR, "monster_zombie.glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_animations=True,
        export_skins=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("DYNAMIC_ZOMBIE ->", glb_path)
    return glb_path


# --------------------------------------------------------------------------
# 2b. 动态资源: 潜行怪物 (仿致命公司 Bracken, transformative derivative)
# --------------------------------------------------------------------------
def build_bracken():
    clear_scene()
    scene = bpy.context.scene
    scene.render.fps = 24

    m_skin = make_material("M_Bracken_Skin", (0.15, 0.15, 0.17), 0.85, 0.0)
    m_cloth = make_material("M_Bracken_Cloth", (0.10, 0.10, 0.12), 0.95, 0.0)

    arm_obj = build_armature(BONES_BRACKEN, "SK_Bracken_Armature")

    mesh_parts = []
    for pname, loc, size, bone_name in BRACKEN_PARTS:
        mat = m_cloth if pname.startswith(("torso", "pelvis", "leg_up", "leg_lo")) else m_skin
        ob = box("SK_Bracken_" + pname, loc, size, mat)
        add_verts_to_group(ob, bone_name)
        mesh_parts.append(ob)
    body = join_objects(mesh_parts, "SK_Bracken_Body")
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj
    body.parent = arm_obj
    body.matrix_parent_inverse = arm_obj.matrix_world.inverted()

    # walk (慢速潜行, 弯腰前倾)
    f = [1, 9, 17, 25]
    walk_tracks = {
        "leg_up.L": (f, [0.30, 0.0, -0.25, 0.0], "rotation_euler", 0),
        "leg_up.R": (f, [-0.25, 0.0, 0.30, 0.0], "rotation_euler", 0),
        "leg_lo.L": (f, [-0.12, -0.45, -0.18, -0.08], "rotation_euler", 0),
        "leg_lo.R": (f, [-0.18, -0.08, -0.12, -0.45], "rotation_euler", 0),
        "arm_up.L": (f, [1.0, 1.1, 1.0, 1.1], "rotation_euler", 0),  # 长臂前伸
        "arm_up.R": (f, [1.1, 1.0, 1.1, 1.0], "rotation_euler", 0),
        "spine":    (f, [0.15, 0.10, 0.15, 0.10], "rotation_euler", 0),
        "pelvis":   (f, [0.01, 0.03, 0.01, 0.03], "location", 2),
    }
    build_animation(arm_obj, "walk", 25, walk_tracks)

    # idle (潜伏晃动)
    fi = [1, 21, 41]
    idle_tracks = {
        "spine":  (fi, [0.12, 0.18, 0.12], "rotation_euler", 0),
        "head":   (fi, [-0.05, 0.08, -0.05], "rotation_euler", 0),
        "pelvis": (fi, [0.0, 0.015, 0.0], "location", 2),
    }
    build_animation(arm_obj, "idle", 40, idle_tracks)

    blend_path = os.path.join(SRC_DIR, "monster_bracken.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    glb_path = os.path.join(DYN_DIR, "monster_bracken.glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_animations=True,
        export_skins=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("DYNAMIC_BRACKEN ->", glb_path)
    return glb_path


# --------------------------------------------------------------------------
# 2c. 动态资源: 线圈头怪物 (仿致命公司 Coil-Head, transformative derivative)
# --------------------------------------------------------------------------
def build_coil():
    clear_scene()
    scene = bpy.context.scene
    scene.render.fps = 24

    m_body = make_material("M_Coil_Body", (0.55, 0.50, 0.42), 0.8, 0.1)
    m_coil = make_material("M_Coil_Head", (0.40, 0.38, 0.35), 0.5, 0.7)

    arm_obj = build_armature(BONES, "SK_Coil_Armature")  # 复用僵尸直立骨架

    mesh_parts = []
    for pname, loc, size, bone_name in COIL_PARTS:
        mat = m_coil if pname in ("neck_spring", "coil_head") else m_body
        ob = box("SK_Coil_" + pname, loc, size, mat)
        add_verts_to_group(ob, bone_name)
        mesh_parts.append(ob)
    body = join_objects(mesh_parts, "SK_Coil_Body")
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj
    body.parent = arm_obj
    body.matrix_parent_inverse = arm_obj.matrix_world.inverted()

    # walk (踱步 + 头部持续旋转, Y 轴)
    f = [1, 9, 17, 25]
    walk_tracks = {
        "leg_up.L": (f, [0.35, 0.0, -0.30, 0.0], "rotation_euler", 0),
        "leg_up.R": (f, [-0.30, 0.0, 0.35, 0.0], "rotation_euler", 0),
        "leg_lo.L": (f, [-0.08, -0.55, -0.18, -0.06], "rotation_euler", 0),
        "leg_lo.R": (f, [-0.18, -0.06, -0.08, -0.55], "rotation_euler", 0),
        "arm_up.L": (f, [0.6, 0.7, 0.6, 0.7], "rotation_euler", 0),
        "arm_up.R": (f, [0.7, 0.6, 0.7, 0.6], "rotation_euler", 0),
        "head":    (f, [0.0, 1.5, 3.0, 4.5], "rotation_euler", 1),
    }
    build_animation(arm_obj, "walk", 25, walk_tracks)

    # idle (站立 + 缓慢旋转头部)
    fi = [1, 13, 25, 37, 49]
    idle_tracks = {
        "head":  (fi, [0.0, 1.2, 2.4, 3.6, 4.8], "rotation_euler", 1),
        "spine": (fi, [0.04, 0.06, 0.04, 0.06, 0.04], "rotation_euler", 0),
    }
    build_animation(arm_obj, "idle", 48, idle_tracks)

    blend_path = os.path.join(SRC_DIR, "monster_coil.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    glb_path = os.path.join(DYN_DIR, "monster_coil.glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_animations=True,
        export_skins=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("DYNAMIC_COIL ->", glb_path)
    return glb_path


# --------------------------------------------------------------------------
# 2d. 动态资源: 森林巨人 (仿致命公司 Forest Giant, transformative derivative)
#     复用僵尸 BONES / ZOMBIE_PARTS 按比例放大, 加发光大眼, 缓慢沉重步态
# --------------------------------------------------------------------------
GIANT_SCALE = 2.1


def _scale_bones(bones, s):
    out = []
    for name, head, tail, parent in bones:
        h = tuple(round(c * s, 3) for c in head)
        t = tuple(round(c * s, 3) for c in tail)
        out.append((name, h, t, parent))
    return out


def _scale_parts(parts, s):
    out = []
    for pname, loc, size, bone in parts:
        l = tuple(round(c * s, 3) for c in loc)
        z = tuple(round(c * s, 3) for c in size)
        out.append((pname, l, z, bone))
    return out


def build_giant():
    clear_scene()
    scene = bpy.context.scene
    scene.render.fps = 24

    m_skin = make_material("M_Giant_Skin", (0.42, 0.44, 0.40), 0.95, 0.0)   # 灰绿
    m_cloth = make_material("M_Giant_Cloth", (0.30, 0.28, 0.24), 0.95, 0.0)
    m_eye = make_emissive("M_Giant_Eye", (0.90, 0.95, 1.0), 3.0)

    s = GIANT_SCALE
    bones = _scale_bones(BONES, s)
    arm_obj = build_armature(bones, "SK_Giant_Armature")

    # 由僵尸部件放大, 头部额外加两只发光大眼
    parts = _scale_parts(ZOMBIE_PARTS, s)
    eye_z = 1.70 * s
    eye_y = 0.13 * s
    parts.append(("eye.L", (0.07 * s, eye_y, eye_z), (0.07, 0.05, 0.07), "head"))
    parts.append(("eye.R", (-0.07 * s, eye_y, eye_z), (0.07, 0.05, 0.07), "head"))

    mesh_parts = []
    for pname, loc, size, bone_name in parts:
        if pname.startswith("eye"):
            mat = m_eye
        else:
            mat = m_cloth if pname.startswith(("torso", "pelvis", "leg_up", "leg_lo")) else m_skin
        ob = box("SK_Giant_" + pname, loc, size, mat)
        add_verts_to_group(ob, bone_name)
        mesh_parts.append(ob)
    body = join_objects(mesh_parts, "SK_Giant_Body")
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj
    body.parent = arm_obj
    body.matrix_parent_inverse = arm_obj.matrix_world.inverted()

    # walk (缓慢沉重, 大跨步, 手臂下垂)
    f = [1, 13, 25, 37, 49]
    walk_tracks = {
        "leg_up.L": (f, [0.55, 0.0, -0.50, 0.0, 0.55], "rotation_euler", 0),
        "leg_up.R": (f, [-0.50, 0.0, 0.55, 0.0, -0.50], "rotation_euler", 0),
        "leg_lo.L": (f, [-0.10, -0.70, -0.20, -0.06, -0.10], "rotation_euler", 0),
        "leg_lo.R": (f, [-0.20, -0.06, -0.10, -0.70, -0.20], "rotation_euler", 0),
        "arm_up.L": (f, [0.15, 0.20, 0.15, 0.20, 0.15], "rotation_euler", 0),  # 手臂几乎下垂
        "arm_up.R": (f, [0.20, 0.15, 0.20, 0.15, 0.20], "rotation_euler", 0),
        "spine":    (f, [0.10, 0.06, 0.10, 0.06, 0.10], "rotation_euler", 0),
        "pelvis":   (f, [0.02, 0.06, 0.02, 0.06, 0.02], "location", 2),
    }
    build_animation(arm_obj, "walk", 48, walk_tracks)

    # idle (缓慢摇晃 + 头部左右扫视)
    fi = [1, 25, 49, 73, 97]
    idle_tracks = {
        "spine":  (fi, [0.08, 0.12, 0.08, 0.12, 0.08], "rotation_euler", 0),
        "head":   (fi, [-0.15, 0.15, -0.15, 0.15, -0.15], "rotation_euler", 1),
        "pelvis": (fi, [0.0, 0.03, 0.0, 0.03, 0.0], "location", 2),
    }
    build_animation(arm_obj, "idle", 96, idle_tracks)

    blend_path = os.path.join(SRC_DIR, "monster_giant.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    glb_path = os.path.join(DYN_DIR, "monster_giant.glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_animations=True,
        export_skins=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("DYNAMIC_GIANT ->", glb_path)
    return glb_path


def _cyl(name, loc, radius, depth, mat, rot=(0, 0, 0)):
    """创建一个轴向圆柱（用于管道 / 天线 / 底座）。loc/size 为 (x, y, z)。"""
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=loc, rotation=rot)
    ob = bpy.context.object
    ob.name = name
    ob.data.name = name + "_Mesh"
    if mat:
        ob.data.materials.append(mat)
    return ob


# --------------------------------------------------------------------------
# 3. 动态资源: 第一人称武器 (无骨架, 手持拾取物, 贴合 Kenney blaster 配色)
# --------------------------------------------------------------------------
def build_weapon():
    clear_scene()
    m_yellow = make_material("M_Gun_Yellow", (0.85, 0.68, 0.12), 0.55, 0.2)
    m_dark = make_material("M_Gun_Dark", (0.12, 0.12, 0.13), 0.6, 0.7)
    m_glass = make_material("M_Gun_Glass", (0.40, 0.85, 0.95), 0.15, 0.0)
    parts = []
    # 枪身 (沿 +Y 为前)
    parts.append(box("SM_Gun_Body", (0, 0, 0), (0.34, 0.13, 0.15), m_yellow))
    # 枪管
    parts.append(_cyl("SM_Gun_Barrel", (0, 0.20, 0), 0.05, 0.18, m_dark, (math.pi / 2, 0, 0)))
    # 握把
    parts.append(box("SM_Gun_Grip", (-0.02, -0.05, -0.14), (0.10, 0.10, 0.28), m_dark))
    # 瞄准 / 发射器
    parts.append(box("SM_Gun_Emitter", (0, 0.27, 0.0), (0.07, 0.08, 0.10), m_glass))
    # 弹匣
    parts.append(box("SM_Gun_Mag", (-0.02, -0.02, -0.04), (0.08, 0.10, 0.18), m_dark))

    blend_path = os.path.join(SRC_DIR, "weapon_blaster.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    glb_path = os.path.join(DYN_DIR, "weapon_blaster.glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("DYNAMIC_WEAPON ->", glb_path)
    return glb_path


# --------------------------------------------------------------------------
# 3b. 动态资源: 泵动霰弹枪 (第一人称, Kenney 风格配色: 钢身 + 黄强调)
# --------------------------------------------------------------------------
def build_shotgun():
    clear_scene()
    m_body = make_material("M_SG_Body", (0.16, 0.16, 0.18), 0.6, 0.7)
    m_metal = make_material("M_SG_Metal", (0.45, 0.47, 0.50), 0.4, 0.8)
    m_acc = make_material("M_SG_Accent", (0.85, 0.68, 0.12), 0.55, 0.2)
    parts = []
    # 机匣 / 枪身 (沿 +Y 为前, 渲染时整体绕 Z 旋转 -90° 走侧视)
    parts.append(box("SM_SG_Receiver", (0, 0.0, 0), (0.13, 0.50, 0.14), m_body))
    # 枪管 (圆柱轴沿 +Y)
    parts.append(_cyl("SM_SG_Barrel", (0, 0.32, 0.02), 0.035, 0.42, m_metal, (math.pi / 2, 0, 0)))
    # 泵动护木 (套在枪管根部)
    parts.append(box("SM_SG_Pump", (0, 0.18, 0.0), (0.12, 0.22, 0.12), m_acc))
    # 握把 (往下 + 略后)
    parts.append(box("SM_SG_Grip", (-0.02, -0.04, -0.14), (0.10, 0.10, 0.28), m_body))
    # 枪托 (沿 -Y 往后)
    parts.append(box("SM_SG_Stock", (0, -0.30, 0), (0.10, 0.32, 0.16), m_body))
    # 准星 (机匣顶, 靠前)
    parts.append(box("SM_SG_Sight", (0, 0.20, 0.09), (0.03, 0.08, 0.03), m_metal))

    blend_path = os.path.join(SRC_DIR, "weapon_shotgun.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    glb_path = os.path.join(DYN_DIR, "weapon_shotgun.glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("DYNAMIC_WEAPON2 ->", glb_path)
    return glb_path


# --------------------------------------------------------------------------
# 3c. 动态资源: 铲子 (致命公司招牌近战, transformative derivative: 自有比例/配色)
# --------------------------------------------------------------------------
def build_shovel():
    clear_scene()
    m_wood = make_material("M_Shovel_Wood", (0.42, 0.28, 0.15), 0.95, 0.0)
    m_metal = make_material("M_Shovel_Metal", (0.45, 0.47, 0.50), 0.45, 0.8)
    m_dark = make_material("M_Shovel_Dark", (0.14, 0.14, 0.16), 0.7, 0.4)
    parts = []
    # 长木柄 (沿 +Y 为前)
    parts.append(_cyl("SM_Shovel_Handle", (0, 0.0, 0.0), 0.022, 0.70, m_wood, (math.pi / 2, 0, 0)))
    # 金属铲头 (前, 扁平)
    parts.append(box("SM_Shovel_Blade", (0, 0.42, 0.0), (0.18, 0.26, 0.04), m_metal))
    # 铲头连接颈
    parts.append(box("SM_Shovel_Neck", (0, 0.30, 0.0), (0.06, 0.10, 0.05), m_dark))
    # 尾部 T 形握把
    parts.append(box("SM_Shovel_Grip", (0, -0.34, 0.0), (0.16, 0.05, 0.05), m_dark))

    blend_path = os.path.join(SRC_DIR, "weapon_shovel.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    glb_path = os.path.join(DYN_DIR, "weapon_shovel.glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("DYNAMIC_SHOVEL ->", glb_path)
    return glb_path


# --------------------------------------------------------------------------
# 3d. 动态资源: 电击枪 (Zap Gun, transformative derivative: 自有比例/配色)
# --------------------------------------------------------------------------
def build_zapgun():
    clear_scene()
    m_yellow = make_material("M_Zap_Yellow", (0.85, 0.68, 0.12), 0.55, 0.2)
    m_dark = make_material("M_Zap_Dark", (0.12, 0.12, 0.13), 0.6, 0.7)
    m_metal = make_material("M_Zap_Metal", (0.45, 0.47, 0.50), 0.4, 0.8)
    m_blue = make_emissive("M_Zap_Blue", (0.30, 0.70, 1.0), 4.0)
    parts = []
    # 主机身 (沿 +Y 为前)
    parts.append(box("SM_Zap_Body", (0, 0.0, 0.0), (0.16, 0.32, 0.16), m_yellow))
    # 双电极 (前)
    parts.append(_cyl("SM_Zap_Prong_L", (0.045, 0.20, 0.03), 0.012, 0.10, m_metal, (math.pi / 2, 0, 0)))
    parts.append(_cyl("SM_Zap_Prong_R", (-0.045, 0.20, 0.03), 0.012, 0.10, m_metal, (math.pi / 2, 0, 0)))
    # 电极间电弧发光
    parts.append(box("SM_Zap_Arc", (0, 0.22, 0.03), (0.06, 0.02, 0.02), m_blue))
    # 握把 (往下 + 略后)
    parts.append(box("SM_Zap_Grip", (-0.02, -0.04, -0.13), (0.10, 0.10, 0.26), m_dark))
    # 电池
    parts.append(box("SM_Zap_Battery", (0, -0.02, -0.04), (0.08, 0.10, 0.16), m_dark))

    blend_path = os.path.join(SRC_DIR, "weapon_zapgun.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)

    glb_path = os.path.join(DYN_DIR, "weapon_zapgun.glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("DYNAMIC_ZAPGUN ->", glb_path)
    return glb_path


# --------------------------------------------------------------------------
# 4. 动态资源: scrap 战利品垃圾 (致命公司招牌拾取物, 无骨架)
# --------------------------------------------------------------------------
def _export_scrap(name, builders):
    clear_scene()
    for b in builders:
        b()
    blend_path = os.path.join(SRC_DIR, name + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    glb_path = os.path.join(DYN_DIR, name + ".glb")
    filtered_gltf_export(
        glb_path,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("DYNAMIC_SCRAP ->", glb_path)
    return glb_path


def build_scrap_kit():
    # 注意: 每次 _export_scrap 都会 clear_scene() 清空数据块,
    # 因此材质必须在各自 builder 内部创建, 不能在循环外复用。

    def _cube():
        m_rust = make_material("M_Scrap_Rust", (0.42, 0.26, 0.16), 0.8, 0.45)
        m_metal = make_material("M_Scrap_Metal", (0.45, 0.47, 0.50), 0.5, 0.75)
        box("SM_Scrap_Cube", (0, 0, 0.13), (0.22, 0.22, 0.26), m_rust)
        _cyl("SM_Scrap_Antenna", (0.05, 0, 0.42), 0.012, 0.32, m_metal)

    def _pipe():
        m_metal = make_material("M_Scrap_Metal", (0.45, 0.47, 0.50), 0.5, 0.75)
        _cyl("SM_Scrap_Pipe_A", (0, 0, 0.05), 0.05, 0.40, m_metal, (0, 0, math.pi / 2))
        _cyl("SM_Scrap_Pipe_B", (0.18, 0, 0.05), 0.05, 0.30, m_metal, (math.pi / 2, 0, 0))

    def _orb():
        m_glass = make_material("M_Scrap_Glass", (0.50, 0.80, 0.60), 0.1, 0.0)
        m_metal = make_material("M_Scrap_Metal", (0.45, 0.47, 0.50), 0.5, 0.75)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=(0, 0, 0.20))
        orb = bpy.context.object
        orb.name = "SM_Scrap_Orb"
        orb.data.name = "SM_Scrap_Orb_Mesh"
        orb.data.materials.append(m_glass)
        _cyl("SM_Scrap_OrbBase", (0, 0, 0.04), 0.07, 0.08, m_metal)

    def _bell():
        m_brass = make_material("M_Scrap_Brass", (0.70, 0.55, 0.25), 0.45, 0.7)
        bpy.ops.mesh.primitive_cone_add(radius1=0.18, radius2=0.13, depth=0.22, location=(0, 0, 0.18))
        b = bpy.context.object
        b.name = "SM_Scrap_Bell"
        b.data.name = "SM_Scrap_Bell_Mesh"
        b.data.materials.append(m_brass)

    def _bottle():
        m_glass = make_material("M_Scrap_Glass", (0.50, 0.80, 0.60), 0.1, 0.0)
        m_cork = make_material("M_Scrap_Cork", (0.45, 0.30, 0.18), 0.9, 0.0)
        _cyl("SM_Scrap_Bottle", (0, 0, 0.13), 0.07, 0.22, m_glass)
        _cyl("SM_Scrap_Cork", (0, 0, 0.27), 0.045, 0.04, m_cork)

    def _lamp():
        m_shade = make_emissive("M_Scrap_LampShade", (1.0, 0.85, 0.55), 3.0)
        m_metal = make_material("M_Scrap_Metal", (0.45, 0.47, 0.50), 0.5, 0.75)
        bpy.ops.mesh.primitive_cone_add(radius1=0.13, radius2=0.18, depth=0.20, location=(0, 0, 0.30))
        s = bpy.context.object
        s.name = "SM_Scrap_LampShade"
        s.data.name = "SM_Scrap_LampShade_Mesh"
        s.data.materials.append(m_shade)
        _cyl("SM_Scrap_LampBase", (0, 0, 0.10), 0.04, 0.16, m_metal)

    def _gear():
        m_brass = make_material("M_Scrap_Brass", (0.70, 0.55, 0.25), 0.45, 0.7)
        _cyl("SM_Scrap_GearHub", (0, 0, 0.04), 0.16, 0.06, m_brass)
        for i in range(8):
            ang = i * (math.pi / 4)
            x = math.cos(ang) * 0.20
            y = math.sin(ang) * 0.20
            bpy.ops.mesh.primitive_cube_add(size=0.06, location=(x, y, 0.04))
            t = bpy.context.object
            t.name = "SM_Scrap_GearTooth_%d" % i
            t.data.name = t.name + "_Mesh"
            t.rotation_euler = (0, 0, ang)
            t.data.materials.append(m_brass)

    def _engine():
        m_metal = make_material("M_Scrap_Metal", (0.45, 0.47, 0.50), 0.5, 0.75)
        m_dark = make_material("M_Scrap_Dark", (0.18, 0.18, 0.20), 0.7, 0.5)
        box("SM_Scrap_EngineBlock", (0, 0, 0.18), (0.38, 0.26, 0.32), m_metal)
        box("SM_Scrap_EngineTop", (0, 0, 0.40), (0.28, 0.20, 0.06), m_dark)
        _cyl("SM_Scrap_EngineExhaust_L", (-0.12, 0.10, 0.44), 0.025, 0.10, m_dark)
        _cyl("SM_Scrap_EngineExhaust_R", (0.12, 0.10, 0.44), 0.025, 0.10, m_dark)

    def _book():
        m_red = make_material("M_Scrap_BookRed", (0.55, 0.18, 0.18), 0.7, 0.1)
        m_blue = make_material("M_Scrap_BookBlue", (0.20, 0.30, 0.55), 0.7, 0.1)
        m_pages = make_material("M_Scrap_BookPages", (0.85, 0.80, 0.65), 0.9, 0.0)
        box("SM_Scrap_Book_Red", (-0.08, 0, 0.06), (0.14, 0.20, 0.10), m_red)
        box("SM_Scrap_Book_Blue", (0.08, 0.02, 0.06), (0.14, 0.20, 0.12), m_blue)
        box("SM_Scrap_Book_Pages", (0, 0.11, 0.06), (0.30, 0.02, 0.10), m_pages)

    _export_scrap("scrap_cube", [_cube])
    _export_scrap("scrap_pipe", [_pipe])
    _export_scrap("scrap_orb", [_orb])
    _export_scrap("scrap_bell", [_bell])
    _export_scrap("scrap_bottle", [_bottle])
    _export_scrap("scrap_lamp", [_lamp])
    _export_scrap("scrap_gear", [_gear])
    _export_scrap("scrap_engine", [_engine])
    _export_scrap("scrap_book", [_book])


if __name__ == "__main__":
    builders = [
        ("STATIC_KIT", build_static_kit, 1),
        ("DYNAMIC_ZOMBIE", build_zombie, 2),
        ("DYNAMIC_BRACKEN", build_bracken, 5),
        ("DYNAMIC_COIL", build_coil, 6),
        ("DYNAMIC_GIANT", build_giant, 10),
        ("DYNAMIC_WEAPON", build_weapon, 3),
        ("DYNAMIC_WEAPON2", build_shotgun, 7),
        ("DYNAMIC_SHOVEL", build_shovel, 8),
        ("DYNAMIC_ZAPGUN", build_zapgun, 9),
        ("DYNAMIC_SCRAP", build_scrap_kit, 4),
    ]
    for tag, fn, code in builders:
        try:
            fn()
        except Exception as e:
            print(tag + "_FAILED:", e)
            sys.exit(code)
    print("ALL_DONE")
