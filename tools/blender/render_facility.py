"""三段式设施预览: 大厅内视角 + 全景航拍。"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)

GLB = os.path.join(ROOT, "assets", "maps", "vendor", "facility_three_zone.glb")


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
    # 1) 安检大厅: 值班台+观察窗+双闸门
    shot("facility_hall.png", (1.8, 4.0, 1.65), (9.0, 4.0, 1.2), 24.0, 80.0, 0.55)
    # 2) 灰→黄门槛: 站在迷宫内看穿内墙缺口望向北出口
    shot("facility_maze.png", (14.5, 2.0, 1.7), (22.5, 7.6, 1.1), 24.0, 80.0, 0.65)
    # 3) 工业核心: 西南角拉远机位(避开柱14,14), 反应堆+格栅槽+战利品同框
    shot("facility_core.png", (15.4, 13.0, 2.8), (23.0, 21.0, 1.5), 24.0, 80.0, 0.75)
    # 4) 全景航拍: 全设施 28×36m
    shot("facility_aerial.png", (52.0, -26.0, 50.0), (14.0, 10.0, 0.0), 28.0, 160.0, 1.0)
