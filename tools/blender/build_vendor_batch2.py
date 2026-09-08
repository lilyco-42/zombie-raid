"""第二批 KayKit 收编: Dungeon Remastered (设施内部结构+道具) + Furniture Bits (居住层家具).

复用 build_vendor_lc 的像素级烘压暗管线。火焰/发光材质只做发光增强, 不压暗。
命名处理 `.gltf.glb` 双扩展名。
"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import (filtered_gltf_export, darken_material, boost_glow,
                             VENDOR, ROOT)

STATIC_VENDOR = os.path.join(ROOT, "assets", "static", "vendor")
DUNGEON_DIR = os.path.join(VENDOR, "KayKit-Dungeon-Remastered-1.0",
                           "addons", "kaykit_dungeon_remastered", "Assets", "gltf")
FURN_DIR = os.path.join(VENDOR, "KayKit-Furniture-Bits-1.0",
                        "addons", "kaykit_furniture_bits", "Assets", "gltf")

# 地牢件: 偏暗冷色 (与设施内部一致); 家具: 轻度去饱和, 保持可读
DGN_SAT, DGN_TINT = 0.45, (0.66, 0.68, 0.74)
FRN_SAT, FRN_TINT = 0.55, (0.72, 0.73, 0.78)
GLOW_STRENGTH = 4.0

# 结构件: 走廊/房间拼搭
DUNGEON_STRUCTURE = [
    "wall.gltf.glb", "wall_arched.gltf.glb", "wall_doorway.glb",
    "wall_gated.gltf.glb", "wall_broken.gltf.glb", "wall_corner.gltf.glb",
    "wall_window_closed.gltf.glb", "floor_tile_large.gltf.glb",
    "floor_tile_grate.gltf.glb", "floor_dirt_large.gltf.glb",
    "pillar.gltf.glb", "column.gltf.glb",
    "stairs.gltf.glb", "stairs_narrow.gltf.glb",
]

# 道具件: 内部陈设 + 照明
DUNGEON_PROPS = [
    "torch_lit.gltf.glb", "candle_triple.gltf.glb", "barrel_large.gltf.glb",
    "crates_stacked.gltf.glb", "chest.glb", "table_medium.gltf.glb",
    "chair.gltf.glb", "shelf_large.gltf.glb", "rubble_large.gltf.glb",
    "trunk_medium_A.gltf.glb",
]

# 家具件: 员工区/居住层
FURNITURE_PICKS = [
    "armchair.gltf", "couch.gltf", "cabinet_medium.gltf",
    "shelf_B_large.gltf", "table_low.gltf", "lamp_standing.gltf",
    "bed_single_A.gltf", "rug_rectangle_A.gltf",
]


def clean_name(name):
    """'wall.gltf.glb' / 'wall.gltf' / 'wall.glb' -> 'wall'."""
    n = name
    for ext in (".gltf.glb", ".gltf", ".glb"):
        if n.endswith(ext):
            n = n[: -len(ext)]
            break
    return n


def recolor_scene(sat, tint):
    """火焰/发光材质增强发光, 其余烘压暗。"""
    for mat in bpy.data.materials:
        lname = mat.name.lower()
        if any(k in lname for k in ("fire", "flame", "glow", "light", "lava")):
            boost_glow(mat, GLOW_STRENGTH)
        else:
            darken_material(mat, sat, tint)


def curate_batch(src_dir, names, out_subdir, sat, tint):
    out_dir = os.path.join(STATIC_VENDOR, out_subdir)
    os.makedirs(out_dir, exist_ok=True)
    ok, missing = 0, []
    for name in names:
        src = os.path.join(src_dir, name)
        if not os.path.exists(src):
            missing.append(name)
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=src)
        recolor_scene(sat, tint)
        out = os.path.join(out_dir, clean_name(name) + ".glb")
        filtered_gltf_export(
            out,
            export_format="GLB",
            export_yup=True,
            export_apply=False,
            export_materials="EXPORT",
            export_cameras=False,
            export_lights=False,
        )
        print("CURATED ->", out)
        ok += 1
    return ok, missing


if __name__ == "__main__":
    n1, m1 = curate_batch(DUNGEON_DIR, DUNGEON_STRUCTURE, "dungeon", DGN_SAT, DGN_TINT)
    n2, m2 = curate_batch(DUNGEON_DIR, DUNGEON_PROPS, "dungeon", DGN_SAT, DGN_TINT)
    n3, m3 = curate_batch(FURN_DIR, FURNITURE_PICKS, "furniture", FRN_SAT, FRN_TINT)
    print(f"BATCH2_DONE structure={n1} props={n2} furniture={n3}")
    if m1 or m2 or m3:
        print("MISSING:", m1 + m2 + m3)
