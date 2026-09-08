"""
渲染 vendor 资产预览 (KayKit CC0 包)

用法:
    blender -b --python tools/blender/render_vendor_previews.py

产出 (assets/_previews/):
    vendor_skel_*.png     骷髅角色 (带骨骼动画, 替换方块怪的候选)
    vendor_spacebase.png  太空基地模块网格总览
    vendor_halloween.png  万圣节道具一排
"""

import os
import math
import bpy
import mathutils

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENDOR = os.path.join(ROOT, "assets", "vendor", "kaykit")
OUT = os.path.join(ROOT, "assets", "_previews")
os.makedirs(OUT, exist_ok=True)

SKEL_DIR = os.path.join(VENDOR, "KayKit-Character-Pack-Skeletons-1.0",
                        "addons", "kaykit_character_pack_skeletons", "Characters", "gltf")
SPACE_DIR = os.path.join(VENDOR, "KayKit-Space-Base-Bits-1.0",
                         "addons", "kaykit_space_base_bits", "Assets", "gltf")
HALLOW_DIR = os.path.join(VENDOR, "KayKit-Halloween-Bits-1.0",
                          "addons", "kaykit_halloween_bits", "Assets", "gltf")

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

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.09, 0.09, 0.11, 1.0)
        bg.inputs["Strength"].default_value = 1.2

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


def add_ground(size=30.0, z=-0.02):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    ground = bpy.context.object
    ground.name = "Preview_Ground"
    mat = bpy.data.materials.new("M_PreviewGround")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.07, 0.07, 0.08, 1.0)
        bsdf.inputs["Roughness"].default_value = 1.0
    ground.data.materials.append(mat)
    return ground


def import_gltf(filepath):
    """导入 gltf/glb, 返回新增对象列表。"""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=filepath)
    return [o for o in bpy.data.objects if o not in before]


def pick_action(arm, prefer=("walk", "run", "idle")):
    if not arm or not arm.animation_data:
        return None
    actions = list(bpy.data.actions)
    for key in prefer:
        for a in actions:
            if key in a.name.lower():
                return a
    return actions[0] if actions else None


def render_skeleton(glb_name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_gltf(os.path.join(SKEL_DIR, glb_name))
    arm = next((o for o in objs if o.type == "ARMATURE"), None)
    act = pick_action(arm)
    if arm and act:
        arm.animation_data.action = act
        # 取动作中段帧, 展示姿势
        f0, f1 = act.frame_range
        bpy.context.scene.frame_set(int((f0 + f1) / 2))
    # 让角色正面朝 -Y 相机 (KayKit 角色正面 +Z/glTF => Blender +Y? 先按 180° 试)
    if arm:
        arm.rotation_euler = (0, 0, math.pi)
    add_ground(size=10.0)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.7
    add_camera("Cam_V", (3.1, -4.2, 2.0), (0, 0, 0.9), lens=50.0)
    out = "vendor_skel_" + os.path.splitext(glb_name)[0] + ".png"
    render_to(out)
    print("ACTION_USED ->", glb_name, ":", act.name if act else None)


def render_lc_skeleton(glb_path, out_name):
    """渲染微调收编后的 LC 骷髅 (assets/dynamic/monster_skeleton_*.glb)。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_gltf(glb_path)
    arm = next((o for o in objs if o.type == "ARMATURE"), None)
    act = pick_action(arm)
    if arm and act:
        arm.animation_data.action = act
        f0, f1 = act.frame_range
        bpy.context.scene.frame_set(int((f0 + f1) / 2))
    if arm:
        arm.rotation_euler = (0, 0, math.pi)
    add_ground(size=10.0)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.55  # 调暗环境, 凸显发光大眼
    add_camera("Cam_LC", (3.1, -4.2, 2.0), (0, 0, 0.9), lens=50.0)
    render_to(out_name)


def render_basecamp(glb="base_camp.glb", out="composite_basecamp.png"):
    """拼接场景: mini 月面基地 3/4 航拍。"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_gltf(os.path.join(ROOT, "assets", "maps", "vendor", glb))
    add_ground(size=60.0, z=-0.05)
    setup_scene()
    add_camera("Cam_Base", (19, -17, 12), (5, 2, 0.5), lens=32.0)
    render_to(out)


SPACE_SAMPLE = [
    "basemodule_A.gltf", "basemodule_garage.gltf", "cargodepot_A.gltf",
    "containers_A.gltf", "drill_structure.gltf", "spacetruck.gltf",
    "lander_A.gltf", "landingpad_large.gltf", "tunnel_straight_A.gltf",
    "windturbine_tall.gltf", "solarpanel.gltf", "structure_tall.gltf",
]


def render_spacebase():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cols, spacing = 4, 6.0
    placed = 0
    for name in SPACE_SAMPLE:
        fp = os.path.join(SPACE_DIR, name)
        if not os.path.exists(fp):
            print("MISS ->", name)
            continue
        objs = import_gltf(fp)
        roots = [o for o in objs if o.parent is None]
        x = (placed % cols) * spacing - (cols - 1) * spacing / 2
        y = (placed // cols) * spacing - spacing
        for r in roots:
            r.location.x += x
            r.location.y += y
        placed += 1
    add_ground(size=60.0, z=-0.05)
    setup_scene()
    add_camera("Cam_Space", (10, -14, 8.5), (0, 0, 0.8), lens=35.0)
    render_to("vendor_spacebase.png")


HALLOW_SAMPLE = [
    "coffin.gltf", "gravestone.gltf", "gravemarker_A.gltf",
    "lantern_standing.gltf", "pumpkin_orange_jackolantern.gltf", "bone_A.gltf",
]


def render_halloween():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    spacing = 2.2
    placed = 0
    for name in HALLOW_SAMPLE:
        fp = os.path.join(HALLOW_DIR, name)
        if not os.path.exists(fp):
            print("MISS ->", name)
            continue
        objs = import_gltf(fp)
        roots = [o for o in objs if o.parent is None]
        x = placed * spacing - (len(HALLOW_SAMPLE) - 1) * spacing / 2
        for r in roots:
            r.location.x += x
        placed += 1
    add_ground(size=30.0, z=-0.05)
    setup_scene()
    add_camera("Cam_Hal", (0, -8.5, 2.2), (0, 0, 0.7), lens=42.0)
    render_to("vendor_halloween.png")


if __name__ == "__main__":
    DYN = os.path.join(ROOT, "assets", "dynamic")
    for name in ("monster_skel_minion_axe", "monster_skel_warrior_blade_shield",
                 "monster_skel_rogue_crossbow", "monster_skel_mage_staff"):
        render_lc_skeleton(os.path.join(DYN, name + ".glb"), "composite_" + name + ".png")
    render_basecamp()
    print("VENDOR_PREVIEWS_DONE")
