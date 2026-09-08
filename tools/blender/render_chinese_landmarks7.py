"""中式地标第七批预览: 石凳 / 石圆桌 / 石盆 / 碑林 (全框 + 园居器物近景)。"""
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
    shot("zhlm7_overview.png",
         ["stone_bench", "stone_round_table", "stone_basin", "stone_stele_cluster"], 12.0,
         (18, -30, 11), (18, 0, 2.2), 24.0, 0.40)
    shot("zhlm7_bench.png", ["stone_bench", "stone_round_table"], 3.0,
         (1.5, -9, 2.6), (1.5, 0, 0.9), 32.0, 0.44)
    shot("zhlm7_stele.png", ["stone_stele_cluster"], 0.0,
         (0, -12, 4.5), (0, 0, 1.8), 30.0, 0.44)
    print("ZHLM7_PV_DONE")
