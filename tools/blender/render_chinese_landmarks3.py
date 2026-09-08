"""中式地标第三批预览: 四件全框 + 券门近景 (拱洞/马道/垛口) + 华表/太湖石近景。"""
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
    shot("zhlm3_overview.png", ["beacon_tower", "gate_platform", "huabiao", "taihu_rock"], 12.0,
         (18, -34, 12), (18, 0, 3.0), 24.0, 0.38)
    shot("zhlm3_gate.png", ["gate_platform"], 0.0, (0, -17, 5.0), (0, 0, 3.0), 30.0, 0.42)
    shot("zhlm3_stone.png", ["huabiao", "taihu_rock"], 3.2,
         (1.6, -8.5, 3.0), (1.6, 0, 1.6), 32.0, 0.44)
    print("ZHLM3_PV_DONE")
