"""第三批收编: KayKit Adventures 5 个带骨骼角色 (幸存者/玩家候选), LC 微调。"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import (filtered_gltf_export, darken_material, boost_glow,
                             LC_SAT, LC_TINT, GLOW_STRENGTH, VENDOR, ROOT)

ADV_DIR = os.path.join(VENDOR, "KayKit-Character-Pack-Adventures-1.0",
                       "addons", "kaykit_character_pack_adventures",
                       "Characters", "gltf")
DYN_DIR = os.path.join(ROOT, "assets", "dynamic")

CHARACTERS = [
    ("Barbarian.glb", "survivor_barbarian.glb"),
    ("Knight.glb", "survivor_knight.glb"),
    ("Mage.glb", "survivor_mage.glb"),
    ("Rogue.glb", "survivor_rogue.glb"),
    ("Rogue_Hooded.glb", "survivor_rogue_hooded.glb"),
]


def curate_character(glb_name, out_name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ADV_DIR, glb_name))
    for mat in bpy.data.materials:
        lname = mat.name.lower()
        if "glow" in lname or "eye" in lname:
            boost_glow(mat, GLOW_STRENGTH)
        else:
            darken_material(mat, LC_SAT, LC_TINT)
    out = os.path.join(DYN_DIR, out_name)
    filtered_gltf_export(
        out,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_animations=True,
        export_skins=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("CURATED_ADV ->", out)


if __name__ == "__main__":
    for glb, out in CHARACTERS:
        curate_character(glb, out)
    print("ADVENTURES_DONE")
