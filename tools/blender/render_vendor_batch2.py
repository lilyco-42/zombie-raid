"""渲染第二批收编资产预览: 地牢组 (结构+道具) + 家具组。"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)

DGN_DIR = os.path.join(ROOT, "assets", "static", "vendor", "dungeon")
FRN_DIR = os.path.join(ROOT, "assets", "static", "vendor", "furniture")

DUNGEON_ALL = [
    "wall", "wall_arched", "wall_doorway", "wall_gated", "wall_broken", "wall_corner",
    "wall_window_closed", "floor_tile_large", "floor_tile_grate", "floor_dirt_large",
    "pillar", "column", "stairs", "stairs_narrow",
    "torch_lit", "candle_triple", "barrel_large", "crates_stacked", "chest",
    "table_medium", "chair", "shelf_large", "rubble_large", "trunk_medium_A",
]

FURNITURE_ALL = [
    "armchair", "couch", "cabinet_medium", "shelf_B_large",
    "table_low", "lamp_standing", "bed_single_A", "rug_rectangle_A",
]


def grid_preview(src_dir, names, out_name, cols, spacing, cam_loc, cam_target, lens=35.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for i, name in enumerate(names):
        objs = import_gltf(os.path.join(src_dir, name + ".glb"))
        r, c = divmod(i, cols)
        for o in objs:
            if o.parent is None:
                o.location.x += c * spacing
                o.location.y -= r * spacing
    rows = math.ceil(len(names) / cols)
    w, h = cols * spacing, rows * spacing
    add_ground(size=max(w, h) * 2.2)
    setup_scene()
    add_camera("Cam_Grid", cam_loc, cam_target, lens=lens)
    render_to(out_name)


if __name__ == "__main__":
    grid_preview(DGN_DIR, DUNGEON_ALL, "vendor_dungeon.png", 6, 4.5,
                 (20.5, -25.5, 15.0), (11.2, -5.8, 0.4), lens=28.0)
    grid_preview(FRN_DIR, FURNITURE_ALL, "vendor_furniture.png", 4, 2.8,
                 (8.5, -12.5, 8.5), (4.2, -1.4, 0.4), lens=32.0)
