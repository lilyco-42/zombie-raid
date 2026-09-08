"""中式地标第四批预览: 长城墙段 (垛口/马道/女儿墙) + 石栏杆段 (望柱/栏板)。"""
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
    add_ground(size=120)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, cam_target, lens=lens)
    render_to(out_name)

if __name__ == "__main__":
    shot("zhlm4_overview.png", ["greatwall_section", "stone_railing"], 12.0,
         (9, -22, 10), (9, 0, 3.0), 24.0, 0.40)
    shot("zhlm4_wall.png", ["greatwall_section"], 0.0,
         (0, -16, 5.5), (0, 0, 3.2), 28.0, 0.44)
    shot("zhlm4_railing.png", ["stone_railing"], 0.0,
         (0, -4.5, 1.8), (0, 0, 0.6), 35.0, 0.46)
    print("ZHLM4_PV_DONE")
