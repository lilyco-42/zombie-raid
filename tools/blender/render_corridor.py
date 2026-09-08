"""走廊场景预览: 内部第一人称视角 + 外部航拍各一张。"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)

GLB = os.path.join(ROOT, "assets", "maps", "vendor", "facility_corridor.glb")


def shot(out_name, cam_loc, cam_target, lens, ground_size, light_mult):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_gltf(GLB)
    add_ground(size=ground_size)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, cam_target, lens=lens)
    render_to(out_name)


if __name__ == "__main__":
    # 内部视角: 站在入口内侧朝走廊深处看 (走廊 4m 宽 × 12m 长, 沿 Y 轴)
    shot("corridor_interior.png", (2.0, 0.9, 1.6), (2.0, 9.5, 1.0), 24.0, 40.0, 0.45)
    # 航拍: 3/4 俯视全貌
    shot("corridor_aerial.png", (11.0, -8.0, 12.0), (2.0, 6.0, 0.3), 32.0, 60.0, 1.0)
