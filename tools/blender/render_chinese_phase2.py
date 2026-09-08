"""中式 Phase 2 预览: 大件排站 (遗址类) + 小件排站 (器物类) + 月洞门近景。"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)

ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
BIG = ["dashuifa", "ruin_columns", "screen_wall", "moon_gate"]
SMALL = ["stele", "incense_burner", "water_vat", "ba_xian_table", "stool"]


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
    # 遗址排: 大水法 / 残柱阵 / 照壁 / 月洞门 (全框)
    shot("zh2_ruins.png", BIG, 5.0, (9.0, -20.0, 4.0), (7.5, 0, 1.5), 26.0, 0.34)
    # 器物排: 石碑 / 香炉 / 水缸 / 八仙桌 / 方凳 (全框)
    shot("zh2_props.png", SMALL, 2.2, (4.4, -9.5, 2.6), (4.4, 0, 0.7), 30.0, 0.42)
    # 月洞门近景: 穿洞看后方 (验证 boolean 洞与环)
    shot("zh2_moongate.png", ["moon_gate", "screen_wall"], 6.0,
         (-3.2, -7.5, 1.8), (0.5, 1.0, 1.5), 28.0, 0.40)
    print("ZH2_PV_DONE")
