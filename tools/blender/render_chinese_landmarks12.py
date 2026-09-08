"""中式地标第十二批预览: 石桥栏板组 / 石像生文臣 / 石像生武将 / 石板平桥。"""
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
    shot("zhlm12_overview.png",
         ["bridge_balustrade", "stone_official", "stone_general", "stone_slab_bridge"], 12.0,
         (18, -30, 11), (18, 0, 2.2), 24.0, 0.40)
    shot("zhlm12_figures.png", ["stone_official", "stone_general"], 3.0,
         (1.5, -7.5, 2.4), (1.5, 0, 1.4), 34.0, 0.44)
    shot("zhlm12_bridge.png", ["stone_slab_bridge", "bridge_balustrade"], 10.0,
         (5, -16, 5.0), (5, 0, 1.4), 30.0, 0.44)
    print("ZHLM12_PV_DONE")
