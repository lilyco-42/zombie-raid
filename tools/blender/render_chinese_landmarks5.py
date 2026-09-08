"""中式地标第五批预览: 石经幢 / 拴马桩 / 太液池 / 石灯笼 (全框 + 水池近景)。"""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)
ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")

def shot(out_name, pieces, spacing, cam_loc, cam_target, lens, light_mult):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    x = 0.0
    for p in pieces:
        import_gltf(os.path.join(ZH, p + ".glb"))
        for o in bpy.context.selected_objects:
            o.location.x += x
        x += spacing
    add_ground(size=140)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, cam_target, lens=lens)
    render_to(out_name)

if __name__ == "__main__":
    shot("zhlm5_overview.png",
         ["stone_sutra", "hitching_post", "stone_pool", "stone_lantern"], 12.0,
         (18, -30, 11), (18, 0, 2.6), 24.0, 0.40)
    shot("zhlm5_pool.png", ["stone_pool"], 0.0,
         (0, -14, 4.5), (0, 0, 0.2), 30.0, 0.42)
    shot("zhlm5_stone.png", ["stone_sutra", "stone_lantern"], 3.0,
         (1.5, -9, 3.2), (1.5, 0, 1.6), 32.0, 0.44)
    print("ZHLM5_PV_DONE")
