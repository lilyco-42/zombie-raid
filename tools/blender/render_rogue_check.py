"""One-off: render rogue crossbow from 3/4 side angle to verify attachment."""
import bpy, math, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, pick_action, setup_scene,
                                    add_camera, add_ground, render_to, ROOT)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path = os.path.join(ROOT, "assets", "dynamic", "monster_skel_rogue_crossbow.glb")
    objs = import_gltf(path)
    arm = next((o for o in objs if o.type == "ARMATURE"), None)
    act = pick_action(arm, prefer=("idle", "walk"))
    if arm and act:
        arm.animation_data.action = act
        f0, f1 = act.frame_range
        bpy.context.scene.frame_set(int((f0 + f1) / 2))
    if arm:
        arm.rotation_euler = (0, 0, math.radians(215))  # 3/4 侧后视角, 看右手弩
    add_ground(size=10.0)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.55
    add_camera("Cam_Check", (3.4, -3.6, 1.9), (0, 0, 0.8), lens=50.0)
    render_to("composite_rogue_crossbow_check.png")


main()
