"""中式渐进 · 城内篇布局目检: 按 chinese_district.gd 的坐标在 Blender 里摆一遍。

Godot (x, z) -> Blender (x, -z) [glTF Y-up]。
运行: blender --background --python tools/blender/render_chinese_district.py
"""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)
ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")

INNER = [("brick_pagoda", 4.5, 4.5), ("huabiao", -4.5, 4.5),
         ("bronze_bell", 4.5, -4.5), ("well", -4.5, -4.5)]
MID = [("moon_gate", 4.5, 13.5), ("stone_lion", -4.5, 13.5),
       ("incense_burner", 4.5, -13.5), ("screen_wall", -4.5, -13.5),
       ("taihu_rock", 13.5, 4.5), ("stele", -13.5, 4.5),
       ("stone_lantern", 13.5, -4.5), ("stone_censer", -13.5, -4.5)]
OUTER = [("water_vat", 13.5, 13.5), ("stone_bench", -13.5, 13.5),
         ("hitching_post", 13.5, -13.5), ("mendun", -13.5, -13.5)]


def build():
    for name, gx, gz in INNER + MID + OUTER:
        import_gltf(os.path.join(ZH, name + ".glb"))
        for o in bpy.context.selected_objects:
            o.location.x += gx
            o.location.y += -gz          # Godot z -> Blender -y
            o.rotation_euler[2] += 0.4


def shot(out_name, cam_loc, cam_target, lens, light_mult):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    build()
    add_ground(size=90)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, cam_target, lens=lens)
    render_to(out_name)


if __name__ == "__main__":
    shot("zh_district_top.png", (0, -0.01, 46), (0, 0, 0), 18.0, 0.42)
    shot("zh_district_street.png", (0, -26, 6), (0, -6, 3.0), 26.0, 0.44)
    print("ZH_DISTRICT_PV_DONE")
