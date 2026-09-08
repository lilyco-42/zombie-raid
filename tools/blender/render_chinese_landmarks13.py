"""中式地标第 13 批预览: 长城体系补缺四件 (目检用)。"""
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
    # 登城券门段: 站内侧看券门 + 砖砌登城踏道
    shot("zhlm13_ramp.png", ["greatwall_ramp"], 0.0,
         (7, -19, 7), (0, -2.0, 3.0), 26.0, 0.40)
    # 空心敌楼: 斜看券门面 + 箭窗 + 台顶垛口环
    shot("zhlm13_hollow_tower.png", ["greatwall_hollow_tower"], 0.0,
         (13, -17, 8), (0, 0, 4.2), 26.0, 0.38)
    # 空心敌楼内视: 贴近券门看中室 (验证掏空)
    shot("zhlm13_hollow_tower_in.png", ["greatwall_hollow_tower"], 0.0,
         (0, -9.5, 2.2), (0, 0, 2.4), 30.0, 0.30)
    # 残破断墙段
    shot("zhlm13_ruin.png", ["greatwall_ruin"], 0.0,
         (6, -15, 5.5), (0, 0, 2.4), 28.0, 0.44)
    # 细节墙段: 站外侧看垛口射眼 + 吐水嘴
    shot("zhlm13_section2.png", ["greatwall_section2"], 0.0,
         (5, 13, 7.5), (0, 1.2, 5.6), 30.0, 0.42)
    # 障墙
    shot("zhlm13_barrier.png", ["gw_barrier_wall"], 0.0,
         (3.2, -3.4, 1.4), (0, 0, 0.6), 35.0, 0.46)
    print("ZHLM13_PV_DONE")
