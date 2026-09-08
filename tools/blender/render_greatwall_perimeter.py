"""长城外围 rampart 布局目检: 按 greatwall_perimeter.gd 的摆法在 Blender 里拼一段。

槽位间距 8m, 障墙架在马道面 (z=5.58); 城内(内侧)在 -Y, 城外(垛口)在 +Y。
运行: blender --background --python tools/blender/render_greatwall_perimeter.py
"""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)
ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
DECK_Z = 5.58


def _put(name, x, y=0.0, z=0.0, rot_z=0.0):
    import_gltf(os.path.join(ZH, name + ".glb"))
    for o in bpy.context.selected_objects:
        o.location.x += x
        o.location.y += y
        o.location.z += z
        o.rotation_euler[2] += rot_z


def build_line():
    _put("greatwall_hollow_tower", -1.5, -1.5)          # 敌楼进深大, 往内收
    _put("greatwall_section2", 8.0)
    _put("gw_barrier_wall", 8.0, 0.0, DECK_Z)           # 马道上的障墙
    _put("greatwall_ramp", 16.0)                        # 登城券门段 (踏道朝 -Y 城内)
    _put("greatwall_ruin", 24.0)                        # 残破断墙段
    _put("gw_barrier_wall", 32.0, 0.0, DECK_Z)
    _put("greatwall_section2", 32.0)
    _put("beacon_tower", 41.0, -1.0)                    # 烽火台


def shot(out_name, cam_loc, cam_target, lens, light_mult):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build_line()
    add_ground(size=140)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, cam_target, lens=lens)
    render_to(out_name)


if __name__ == "__main__":
    # 内侧(城内)看: 登城踏道 + 券门 + 敌楼
    shot("gw_perimeter_inner.png", (16, -34, 12), (16, -2, 4.0), 22.0, 0.40)
    # 外侧(城外)看: 垛口射眼 + 吐水嘴 + 敌楼箭窗
    shot("gw_perimeter_outer.png", (16, 30, 11), (16, 2, 4.5), 22.0, 0.42)
    # 俯瞰: 整条防线
    shot("gw_perimeter_top.png", (18, -26, 34), (18, 0, 2.0), 20.0, 0.40)
    print("GW_PERIMETER_PV_DONE")
