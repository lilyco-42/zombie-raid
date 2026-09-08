"""
Blender headless 渲染预览图（替代 HTML 查看器）

用法:
    blender -b --python tools/blender/render_previews.py

产出 (assets/_previews/):
    kit_overview.png      工业关卡套件总览
    zombie_idle.png       僵尸静止姿态（3/4 视角）
    zombie_walk.png       僵尸行走姿态（walk 第 7 帧，侧面，看步幅）
    zombie_walk_sheet.png 行走循环 6 帧序列
"""

import os
import math
import bpy
import mathutils

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "assets", "_src")
OUT = os.path.join(ROOT, "assets", "_previews")
os.makedirs(OUT, exist_ok=True)

RES_X, RES_Y = 1280, 720


def pick_engine():
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    names = [i.identifier for i in items]
    for pref in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES", "BLENDER_WORKBENCH"):
        if pref in names:
            return pref
    return names[0]


def setup_scene():
    sc = bpy.context.scene
    sc.render.engine = pick_engine()
    sc.render.resolution_x = RES_X
    sc.render.resolution_y = RES_Y
    sc.render.film_transparent = False
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = 32
    sc.view_settings.view_transform = "Standard"

    # 世界环境光
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.09, 0.09, 0.11, 1.0)
        bg.inputs["Strength"].default_value = 1.2

    # 三点光（压低能量，避免把低饱和度材质冲成一片白）
    for name, loc, energy, color in (
        ("Key", (8, -10, 12), 12.0, (1.0, 0.96, 0.90)),
        ("Fill", (-10, -6, 6), 3.0, (0.55, 0.62, 0.78)),
        ("Rim", (0, 12, 8), 5.0, (0.75, 0.80, 1.0)),
    ):
        bpy.ops.object.light_add(type="SUN", location=loc)
        lt = bpy.context.object
        lt.name = "Light_" + name
        lt.data.energy = energy
        lt.data.color = color
        lt.rotation_euler = (0.9, 0.0, 0.6)


def add_camera(name, loc, target, lens=50.0):
    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens
    cam = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = loc
    direction = mathutils.Vector(target) - mathutils.Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def render_to(filename):
    path = os.path.join(OUT, filename)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDER ->", path)


# ---------------------------------------------------------------- 静态套件
def render_kit():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, "kit_industrial.blend"))

    objs = [o for o in bpy.data.objects if o.type == "MESH"]
    cols = 6
    for i, ob in enumerate(objs):
        ob.location.x += (i % cols) * 5.0 - 12.0
        ob.location.y += (i // cols) * 5.0 - 8.0

    # 地面
    bpy.ops.mesh.primitive_plane_add(size=60.0, location=(0, 0, -0.35))
    ground = bpy.context.object
    ground.name = "Preview_Ground"
    mat = bpy.data.materials.new("M_PreviewGround")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.07, 0.07, 0.08, 1.0)
        bsdf.inputs["Roughness"].default_value = 1.0
    ground.data.materials.append(mat)

    setup_scene()
    add_camera("Cam_Kit", (16, -22, 13), (0, 0, 1.0), lens=35.0)
    render_to("kit_overview.png")


NEW_PREFIXES = (
    "SM_LC_Camera", "SM_LC_Turnstile", "SM_LC_Siren",
    "SM_LC_Locker", "SM_LC_MonitorWall",
)


def render_lc_facility():
    """只渲染本轮新增的 LC 安防 / 设施模块，单独成图。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, "kit_industrial.blend"))
    matched = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(NEW_PREFIXES)]
    for o in bpy.data.objects:
        if o.type == "MESH" and o not in matched:
            o.hide_render = True
    cols = 3
    for i, ob in enumerate(matched):
        zoff = 1.0 if ob.name in ("SM_LC_Locker", "SM_LC_MonitorWall") else 0.0
        ob.location = ((i % cols) * 2.6 - 2.6, (i // cols) * 2.6 - 1.3, zoff)
    # 地面
    bpy.ops.mesh.primitive_plane_add(size=30.0, location=(0, 0, -0.05))
    ground = bpy.context.object
    ground.name = "Preview_Ground"
    mat = bpy.data.materials.new("M_PreviewGround")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.07, 0.07, 0.08, 1.0)
        bsdf.inputs["Roughness"].default_value = 1.0
    ground.data.materials.append(mat)
    setup_scene()
    # 本图只放 5 个小模块, 默认灯光太亮会把低饱和色冲成白色; 整体压低能量
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.45
    # 正面稍俯视, 拉远一点用广角, 让前排(闸机/警报器)不被后排(柜子/屏墙)完全挡住
    add_camera("Cam_Fac", (0, -11, 4.8), (0, 0.2, 0.6), lens=34.0)
    render_to("lc_facility.png")


NEW_PREFIXES_R7 = (
    "SM_LC_CardReader", "SM_LC_FireExtinguisher", "SM_LC_ElectricBox",
    "SM_LC_VentBend", "SM_LC_Barricade", "SM_LC_Pallet",
)


def render_lc_props():
    """第七轮新增: LC 设施杂项 / 环境道具。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, "kit_industrial.blend"))
    matched = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(NEW_PREFIXES_R7)]
    for o in bpy.data.objects:
        if o.type == "MESH" and o not in matched:
            o.hide_render = True
    # 水平一字排开，1.8m 间距，避免不同高度互相遮挡
    for i, ob in enumerate(matched):
        ob.location = (i * 1.8 - 4.5, 0.0, 0.0)
    # 地面
    bpy.ops.mesh.primitive_plane_add(size=30.0, location=(0, 0, -0.05))
    ground = bpy.context.object
    ground.name = "Preview_Ground"
    mat = bpy.data.materials.new("M_PreviewGround")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.07, 0.07, 0.08, 1.0)
        bsdf.inputs["Roughness"].default_value = 1.0
    ground.data.materials.append(mat)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.55
    add_camera("Cam_Props", (0.0, -9.0, 1.05), (0.0, 0.0, 0.50), lens=42.0)
    render_to("lc_props.png")


# ---------------------------------------------------------------- 僵尸
def _open_zombie():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, "monster_zombie.blend"))
    return bpy.data.objects.get("SK_Zombie_Armature")


def _set_action(arm, action_name, frame):
    if not arm or not arm.animation_data:
        return
    for a in bpy.data.actions:
        if a.name == action_name:
            arm.animation_data.action = a
            break
    bpy.context.scene.frame_set(frame)


def render_zombie():
    # --- idle：3/4 视角 ---
    arm = _open_zombie()
    _set_action(arm, "idle", 1)
    setup_scene()
    add_camera("Cam_Z_Idle", (2.6, -3.4, 1.75), (0, 0.1, 1.05), lens=50.0)
    render_to("zombie_idle.png")

    # --- walk：侧面，看步幅 ---
    arm = _open_zombie()
    _set_action(arm, "walk", 7)
    setup_scene()
    add_camera("Cam_Z_Walk", (4.2, 0.0, 1.15), (0.0, 0.0, 1.05), lens=50.0)
    render_to("zombie_walk.png")


def render_walk_sheet():
    """把 walk 循环 6 帧拼成一张对比图。"""
    frames = [1, 5, 9, 13, 17, 21]
    tile_w, tile_h = 420, 560
    tiles = []

    for idx, f in enumerate(frames):
        arm = _open_zombie()
        _set_action(arm, "walk", f)
        bpy.context.scene.render.resolution_x = tile_w
        bpy.context.scene.render.resolution_y = tile_h
        bpy.context.scene.render.film_transparent = False
        setup_scene()
        add_camera("Cam_Sheet", (4.0, 0.0, 1.15), (0.0, 0.0, 1.05), lens=50.0)
        path = os.path.join(OUT, "_sheet_%02d.png" % idx)
        bpy.context.scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        tiles.append(path)

    # ---- 各帧已渲染为统一灰底 PNG，由外部 Python（带 Pillow）负责拼图 ----
    print("WALK_TILES ->", ";".join(tiles))


# ---------------------------------------------------------------- 潜行怪物 (Bracken-style)
def _open_bracken():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, "monster_bracken.blend"))
    return bpy.data.objects.get("SK_Bracken_Armature")


def render_bracken():
    arm = _open_bracken()
    _set_action(arm, "idle", 1)
    setup_scene()
    add_camera("Cam_B_Idle", (2.4, -3.2, 0.95), (0.15, 0.05, 0.85), lens=50.0)
    render_to("bracken_idle.png")

    arm = _open_bracken()
    _set_action(arm, "walk", 9)
    setup_scene()
    add_camera("Cam_B_Walk", (3.8, 0.0, 0.95), (0.15, 0.0, 0.85), lens=50.0)
    render_to("bracken_walk.png")


# ---------------------------------------------------------------- 线圈头怪物
def _open_coil():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, "monster_coil.blend"))
    return bpy.data.objects.get("SK_Coil_Armature")


def render_coil():
    arm = _open_coil()
    _set_action(arm, "idle", 13)  # 头部旋转中
    setup_scene()
    add_camera("Cam_C_Idle", (2.6, -3.4, 1.75), (0, 0.05, 1.40), lens=50.0)
    render_to("coil_idle.png")

    arm = _open_coil()
    _set_action(arm, "walk", 9)
    setup_scene()
    add_camera("Cam_C_Walk", (4.2, 0.0, 1.15), (0.0, 0.0, 1.30), lens=50.0)
    render_to("coil_walk.png")


# ---------------------------------------------------------------- 森林巨人
def _open_giant():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, "monster_giant.blend"))
    return bpy.data.objects.get("SK_Giant_Armature")


def render_giant():
    # 巨人肤色浅 + 体积大, 三点光会过曝; 且身高 ~3.9m 需拉远相机才能拍全。
    # 正面(+Y)默认朝 -Y 反方向, 旋转 180° 让脸朝向主光/相机一侧, 发光大眼才可见。
    arm = _open_giant()
    _set_action(arm, "idle", 1)
    if arm:
        arm.rotation_euler = (0, 0, math.pi)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.50
    add_camera("Cam_G_Idle", (6.2, -8.2, 3.1), (0, 0.0, 1.9), lens=50.0)
    render_to("giant_idle.png")

    arm = _open_giant()
    _set_action(arm, "walk", 13)
    if arm:
        arm.rotation_euler = (0, 0, math.pi)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.50
    add_camera("Cam_G_Walk", (11.6, 0.0, 2.6), (0.0, 0.0, 1.9), lens=50.0)
    render_to("giant_walk.png")


# ---------------------------------------------------------------- 武器
def render_weapon():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, "weapon_blaster.blend"))
    # 武器原枪管沿 +Y, 从 -Y 拍会被枪身挡住。绕 Z 旋转 -90° 让枪管沿 +X, 走纯侧视。
    bpy.context.view_layer.objects.active = None
    rotated = False
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.rotation_euler = (0.0, 0.0, -math.pi / 2)
            rotated = True
    if rotated:
        bpy.ops.object.select_all(action="SELECT")
        bpy.context.view_layer.objects.active = next(
            (o for o in bpy.data.objects if o.type == "MESH"), None
        )
        bpy.ops.object.transform_apply(rotation=True)
    setup_scene()
    add_camera("Cam_W", (0, -0.9, 0.25), (0, 0, 0), lens=45.0)
    render_to("weapon_blaster.png")


def render_shotgun():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, "weapon_shotgun.blend"))
    # 同 blaster: 枪管沿 +Y, 绕 Z 旋转 -90° 走纯侧视
    bpy.context.view_layer.objects.active = None
    rotated = False
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.rotation_euler = (0.0, 0.0, -math.pi / 2)
            rotated = True
    if rotated:
        bpy.ops.object.select_all(action="SELECT")
        bpy.context.view_layer.objects.active = next(
            (o for o in bpy.data.objects if o.type == "MESH"), None
        )
        bpy.ops.object.transform_apply(rotation=True)
    setup_scene()
    add_camera("Cam_SG", (0, -0.9, 0.25), (0, 0, 0), lens=45.0)
    render_to("weapon_shotgun.png")


def _weapon_side_view(blend_file, cam_name, out_name, cam_dist=-0.9, cam_z=0.25, lens=45.0):
    """通用: 武器原枪管/柄沿 +Y, 挂到空物体下整体绕 Z 转 -90° 走纯侧视。

    用父级 Empty 旋转而非逐件改 rotation_euler, 以保留圆柱等子件的局部朝向
    (逐件覆盖会把沿 Y 的圆柱错误地变回沿 Z)。
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, blend_file))
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    root = bpy.data.objects.new("Weapon_Root", None)
    bpy.context.scene.collection.objects.link(root)
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = root
        o.matrix_world = mw
    root.rotation_euler = (0.0, 0.0, -math.pi / 2)
    setup_scene()
    add_camera(cam_name, (0, cam_dist, cam_z), (0, 0, 0), lens=lens)
    render_to(out_name)


def render_shovel():
    _weapon_side_view("weapon_shovel.blend", "Cam_Sh", "weapon_shovel.png",
                      cam_dist=-1.35, cam_z=0.1, lens=45.0)


def render_zapgun():
    _weapon_side_view("weapon_zapgun.blend", "Cam_Zap", "weapon_zapgun.png",
                      cam_dist=-1.05, cam_z=0.1, lens=45.0)


# ---------------------------------------------------------------- scrap
def render_scrap():
    for name in ("scrap_cube", "scrap_pipe", "scrap_orb", "scrap_bell", "scrap_bottle", "scrap_lamp", "scrap_gear", "scrap_engine", "scrap_book"):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.wm.open_mainfile(filepath=os.path.join(SRC, name + ".blend"))
        setup_scene()
        add_camera("Cam_S", (0.55, -0.75, 0.35), (0, 0, 0.15), lens=45.0)
        render_to(name + ".png")


if __name__ == "__main__":
    render_kit()
    render_lc_facility()
    render_lc_props()
    render_zombie()
    render_bracken()
    render_coil()
    render_giant()
    render_walk_sheet()
    render_weapon()
    render_shotgun()
    render_shovel()
    render_zapgun()
    render_scrap()
    print("PREVIEWS_DONE")