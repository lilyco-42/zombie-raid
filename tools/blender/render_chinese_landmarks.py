"""中式地标预览: 三件全框 + 敌台正面近景 (券门/垛口验证)。"""
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
    shot("zhlm_overview.png", ["greatwall_tower", "brick_pagoda", "stone_bridge"], 14.0,
         (20, -42, 17), (14, 0, 4), 24.0, 0.36)
    shot("zhlm_tower.png", ["greatwall_tower"], 0.0,
         (0, -17, 5.5), (0, 0, 3.4), 30.0, 0.40)
    print("ZHLM_PV_DONE")
