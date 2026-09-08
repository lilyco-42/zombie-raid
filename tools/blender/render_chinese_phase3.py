"""中式 Phase 3 预览: 牌坊正面近景 + 器物排站。"""
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
    add_ground(size=60)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, cam_target, lens=lens)
    render_to(out_name)

if __name__ == "__main__":
    # 牌坊正面 (联/匾字向验证)
    shot("zh3_paifang.png", ["paifang"], 0.0, (0.0, -9.0, 2.6), (0.0, 0, 2.1), 34.0, 0.42)
    # 器物排: 门墩 / 铜钟 / 井台 / 供桌 / 灰堆
    shot("zh3_props.png", ["mendun", "bronze_bell", "well", "offering_table", "paper_ash"],
         2.6, (5.2, -10.0, 2.6), (5.2, 0, 0.8), 30.0, 0.42)
    print("ZH3_PV_DONE")
