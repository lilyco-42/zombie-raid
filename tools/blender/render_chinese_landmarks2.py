"""中式地标第二批预览: 三件全框 + 土楼近景 (门洞/残破/窗) + 圜丘近景。"""
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
    shot("zhlm2_overview.png", ["tulou", "circular_altar", "grotto_cliff"], 22.0,
         (24, -52, 20), (22, 0, 4), 22.0, 0.36)
    shot("zhlm2_tulou.png", ["tulou"], 0.0, (0, -26, 9), (0, 0, 4.0), 26.0, 0.40)
    shot("zhlm2_altar.png", ["circular_altar"], 0.0, (0, -13, 6), (0, 0, 0.9), 30.0, 0.44)
    print("ZHLM2_PV_DONE")
