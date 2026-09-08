"""中式地标第九批预览: 六角石亭 / 石经幢群 / 镇水兽 / 望柱石狮。"""
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
    shot("zhlm9_overview.png",
         ["stone_hex_pavilion", "sutra_cluster", "stone_water_beast", "lion_post"], 12.0,
         (18, -30, 11), (18, 0, 2.2), 24.0, 0.40)
    shot("zhlm9_hex.png", ["stone_hex_pavilion"], 0.0,
         (0, -13, 4.5), (0, 0, 1.5), 32.0, 0.44)
    shot("zhlm9_beasts.png", ["sutra_cluster", "stone_water_beast", "lion_post"], 6.0,
         (8, -14, 4.0), (8, 0, 1.4), 30.0, 0.44)
    print("ZHLM9_PV_DONE")
