"""zombie-raid 地图总览 (俯瞰目检): 长城 rampart + 城市街区代理 + 道路 + 城内中式。

完全按游戏落位脚本的坐标摆:
  greatwall_perimeter.gd  (四边 8m 槽位, 敌楼/烽火台内收 1.5)
  chinese_district.gd     (16 件三档)
  city_builder.gd         (block 中心 +-9/+-24, 道路 -18/0/18)
坐标换算: Godot (x, z, yaw) -> Blender (x, -z, rot_z=yaw)
运行: blender --background --python tools/blender/render_map_overview.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)
ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")

RADIUS = 30.5
TOWER_R = 29.0
DECK_Z = 5.58
SLOTS = [-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0]
MODEL = {"sec": "greatwall_section2", "ramp": "greatwall_ramp",
         "ruin": "greatwall_ruin", "tower": "greatwall_hollow_tower",
         "beacon": "beacon_tower"}
SIDES = [
    ("north", 0.0, ["tower", "sec", "ramp", "sec", "sec", "sec", "ruin", "sec"]),
    ("south", math.pi, ["sec", "sec", "sec", "ramp", "sec", "sec", "ruin", "tower"]),
    ("east", -math.pi / 2, ["sec", "sec", "ramp", "sec", "sec", "beacon", "sec", "sec"]),
    ("west", math.pi / 2, ["sec", "ruin", "sec", "sec", "ramp", "sec", "sec", "sec"]),
]
DISTRICT = [
    ("brick_pagoda", 4.5, 4.5), ("huabiao", -4.5, 4.5),
    ("bronze_bell", 4.5, -4.5), ("well", -4.5, -4.5),
    ("moon_gate", 4.5, 13.5), ("stone_lion", -4.5, 13.5),
    ("incense_burner", 4.5, -13.5), ("screen_wall", -4.5, -13.5),
    ("taihu_rock", 13.5, 4.5), ("stele", -13.5, 4.5),
    ("stone_lantern", 13.5, -4.5), ("stone_censer", -13.5, -4.5),
    ("water_vat", 13.5, 13.5), ("stone_bench", -13.5, 13.5),
    ("hitching_post", 13.5, -13.5), ("mendun", -13.5, -13.5),
]


def _put(name, gx, gz, gz_up, yaw):
    """Godot (x, z, 抬高, yaw) -> Blender。"""
    import_gltf(os.path.join(ZH, name + ".glb"))
    for o in bpy.context.selected_objects:
        o.location.x += gx
        o.location.y += -gz
        o.location.z += gz_up
        o.rotation_euler[2] += yaw


def _wall():
    for tag, yaw, kinds in SIDES:
        for i, kind in enumerate(kinds):
            along = SLOTS[i]
            if tag == "north":
                x, z = along, -RADIUS
            elif tag == "south":
                x, z = along, RADIUS
            elif tag == "east":
                x, z = RADIUS, along
            else:
                x, z = -RADIUS, along
            if kind in ("tower", "beacon"):
                if tag == "north":
                    z += RADIUS - TOWER_R
                elif tag == "south":
                    z -= RADIUS - TOWER_R
                elif tag == "east":
                    x -= RADIUS - TOWER_R
                else:
                    x += RADIUS - TOWER_R
            _put(MODEL[kind], x, z, 0.0, yaw)
            if kind == "sec" and i % 3 == 1:
                _put("gw_barrier_wall", x, z, DECK_Z, yaw)


def _city_proxy():
    """城市街区代理盒 + 道路 (只求看清布局关系)。"""
    road_mat = bpy.data.materials.new("M_Road")
    road_mat.diffuse_color = (0.20, 0.20, 0.22, 1.0)
    bld_mat = bpy.data.materials.new("M_BldProxy")
    bld_mat.diffuse_color = (0.34, 0.34, 0.36, 1.0)
    for c in (-18.0, 0.0, 18.0):
        for horizontal in (True, False):
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            ob = bpy.context.active_object
            ob.scale = (30.0, 3.0, 0.02) if horizontal else (3.0, 30.0, 0.02)
            ob.location = (0.0, -c, 0.02) if horizontal else (c, 0.0, 0.02)
            ob.data.materials.append(road_mat)
    for bx in (-24.0, -9.0, 9.0, 24.0):
        for bz in (-24.0, -9.0, 9.0, 24.0):
            bpy.ops.mesh.primitive_cube_add(size=1.0)
            ob = bpy.context.active_object
            h = 8.0
            ob.scale = (4.2, 4.2, h)
            ob.location = (bx, -bz, h)
            ob.data.materials.append(bld_mat)


def _district():
    for name, gx, gz in DISTRICT:
        _put(name, gx, gz, 0.0, 0.4)


def shot(out_name, cam_loc, cam_target, lens, light_mult):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _city_proxy()
    _wall()
    _district()
    add_ground(size=140)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, cam_target, lens=lens)
    render_to(out_name)


if __name__ == "__main__":
    shot("map_overview_top.png", (0, -0.01, 96), (0, 0, 0), 16.0, 0.42)
    shot("map_overview_3q.png", (58, -58, 42), (0, 0, 3), 20.0, 0.42)
    print("MAP_OVERVIEW_DONE")
