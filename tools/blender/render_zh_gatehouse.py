"""厂区大门组合场景预览: 正面 + 院内 3/4 视角。"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)

GLB = os.path.join(ROOT, "assets", "maps", "vendor", "zh_gatehouse.glb")


def shot(out_name, cam_loc, cam_target, lens, light_mult):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_gltf(GLB)
    add_ground(size=70)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, cam_target, lens=lens)
    render_to(out_name)


if __name__ == "__main__":
    shot("zh_gatehouse_front.png", (4.0, -17.5, 2.4), (4.0, -1.5, 1.6), 30.0, 0.32)
    # 院内视角: 相机站院子里看传达室角 + 标语板
    shot("zh_gatehouse_yard.png", (7.6, -2.2, 2.3), (1.2, 2.6, 1.0), 26.0, 0.45)
    print("ZH_GH_PV_DONE")
