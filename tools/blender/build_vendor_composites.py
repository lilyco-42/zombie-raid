"""
KayKit 复合叠加 / 拼接构建脚本 (CC0)

用法:
    blender -b --python tools/blender/build_vendor_composites.py

产物:
    1. 武装骷髅怪物 (老素材复合: 骷髅角色 + 武器配件挂 handslot 骨)
       -> assets/dynamic/monster_skel_*.glb
       同样走 LC 微调: 贴图烘暗 + 眼睛发光增强, 全套动画保留。
    2. 拼接场景: 太空基地模块拼成 mini 月面基地
       -> assets/maps/vendor/base_camp.glb
"""

import os
import sys
import bpy
from mathutils import Matrix

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from build_vendor_lc import (  # noqa: E402
    VENDOR, DYN_DIR, SKEL_DIR, SPACE_DIR,
    filtered_gltf_export, darken_material, boost_glow,
    LC_SAT, LC_TINT, GLOW_STRENGTH,
)

ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
MAPS_VENDOR = os.path.join(ROOT, "assets", "maps", "vendor")
os.makedirs(MAPS_VENDOR, exist_ok=True)

WEAPON_DIR = os.path.join(VENDOR, "KayKit-Character-Pack-Skeletons-1.0",
                          "addons", "kaykit_character_pack_skeletons", "Assets", "gltf")


def import_gltf(filepath):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=filepath)
    return [o for o in bpy.data.objects if o not in before]


def lc_recolor():
    """对当前场景所有材质做 LC 微调 (贴图烘暗 + 眼睛发光增强)。"""
    for mat in bpy.data.materials:
        lname = mat.name.lower()
        if "glow" in lname or "eye" in lname:
            boost_glow(mat, GLOW_STRENGTH)
        else:
            darken_material(mat, LC_SAT, LC_TINT)


def attach_to_slot(arm_obj, weapon_objs, slot):
    """把武器挂到手部插槽骨 (KayKit handslot 约定: 武器原点=握点, 局部单位阵对齐)。"""
    root = next((o for o in weapon_objs if o.parent is None), None)
    if not root:
        return
    root.parent = arm_obj
    root.parent_type = "BONE"
    root.parent_bone = slot
    root.matrix_basis = Matrix.Identity(4)


def build_armed_skeleton(char_glb, out_name, attachments):
    """attachments: [(weapon_gltf, slot), ...]"""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_gltf(os.path.join(SKEL_DIR, char_glb))
    arm = next(o for o in objs if o.type == "ARMATURE")
    for weapon_file, slot in attachments:
        wobjs = import_gltf(os.path.join(WEAPON_DIR, weapon_file))
        attach_to_slot(arm, wobjs, slot)
    lc_recolor()
    out = os.path.join(DYN_DIR, out_name)
    filtered_gltf_export(
        out,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_animations=True,
        export_skins=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("COMPOSITE_ARMED ->", out)


ARMED_VARIANTS = [
    ("Skeleton_Minion.glb", "monster_skel_minion_axe.glb",
     [("Skeleton_Axe.gltf", "handslot.r")]),
    ("Skeleton_Warrior.glb", "monster_skel_warrior_blade_shield.glb",
     [("Skeleton_Blade.gltf", "handslot.r"), ("Skeleton_Shield_Large_A.gltf", "handslot.l")]),
    ("Skeleton_Rogue.glb", "monster_skel_rogue_crossbow.glb",
     [("Skeleton_Crossbow.gltf", "handslot.r")]),
    ("Skeleton_Mage.glb", "monster_skel_mage_staff.glb",
     [("Skeleton_Staff.gltf", "handslot.r")]),
]


# --------------------------------------------------------------------------
# 拼接场景: mini 月面基地
# --------------------------------------------------------------------------
BASE_LAYOUT = [
    # file, x, y, rot_z(度)
    ("basemodule_A.gltf", 0.0, 0.0, 0),
    ("tunnel_straight_A.gltf", 3.6, 0.0, 0),
    ("basemodule_garage.gltf", 7.2, 0.0, 0),
    ("landingpad_large.gltf", 11.5, 3.0, 0),
    ("lander_A.gltf", 11.5, 3.0, 0),
    ("containers_A.gltf", 1.5, 4.2, 10),
    ("cargodepot_A.gltf", 5.5, 4.4, 0),
    ("drill_structure.gltf", 10.0, 5.5, 0),
    ("windturbine_tall.gltf", -3.2, 2.0, 0),
    ("solarpanel.gltf", -3.2, 5.0, -20),
    ("spacetruck.gltf", 2.5, -3.4, 15),
    ("structure_tall.gltf", 13.5, 6.0, 0),
]


def build_base_camp():
    import math
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name, x, y, rot in BASE_LAYOUT:
        objs = import_gltf(os.path.join(SPACE_DIR, name))
        for o in objs:
            if o.parent is None:
                o.location.x += x
                o.location.y += y
                o.rotation_euler.z = math.radians(rot)
    out = os.path.join(MAPS_VENDOR, "base_camp.glb")
    filtered_gltf_export(
        out,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("COMPOSITE_BASECAMP ->", out)


def build_base_camp_dark():
    """用 space_dark 压暗变体重建基地 (文件名 .gltf -> .glb)。"""
    import math
    dark_dir = os.path.join(ROOT, "assets", "static", "vendor", "space_dark")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for name, x, y, rot in BASE_LAYOUT:
        glb = name.replace(".gltf", ".glb")
        objs = import_gltf(os.path.join(dark_dir, glb))
        for o in objs:
            if o.parent is None:
                o.location.x += x
                o.location.y += y
                o.rotation_euler.z = math.radians(rot)
    out = os.path.join(MAPS_VENDOR, "base_camp_dark.glb")
    filtered_gltf_export(
        out,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("COMPOSITE_BASECAMP_DARK ->", out)


if __name__ == "__main__":
    if "--dark-only" in sys.argv:
        build_base_camp_dark()
        sys.exit(0)
    for char, out, att in ARMED_VARIANTS:
        build_armed_skeleton(char, out, att)
    build_base_camp()
    print("COMPOSITES_DONE")
