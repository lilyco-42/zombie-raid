"""幸存者 5 角色一字排开预览。"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, pick_action, setup_scene,
                                    add_camera, add_ground, render_to, ROOT)

DYN = os.path.join(ROOT, "assets", "dynamic")
NAMES = ["survivor_barbarian", "survivor_knight", "survivor_mage",
         "survivor_rogue", "survivor_rogue_hooded"]


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    spacing = 1.5
    for i, name in enumerate(NAMES):
        objs = import_gltf(os.path.join(DYN, name + ".glb"))
        arm = next((o for o in objs if o.type == "ARMATURE"), None)
        if arm:
            arm.location.x = i * spacing
            arm.rotation_euler.z = math.pi  # 面向 -Y 相机
            act = pick_action(arm, prefer=("idle", "walk"))
            if act:
                arm.animation_data.action = act
    bpy.context.scene.frame_set(20)
    add_ground(size=14.0)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.6
    cx = (len(NAMES) - 1) * spacing / 2
    add_camera("Cam", (cx + 0.5, -9.2, 2.4), (cx, 0, 0.85), lens=42.0)
    render_to("vendor_adventures.png")


main()
