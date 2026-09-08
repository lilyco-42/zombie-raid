"""
KayKit vendor 资产微调收编脚本 (全部 CC0)

用法:
    blender -b --python tools/blender/build_vendor_lc.py

做的事:
    1. 骷髅角色包 -> assets/dynamic/monster_skeleton_*.glb
       微调: skeleton 贴图材质插入 Hue/Saturation 节点(去饱和+压暗 -> LC 阴森工业风),
             Glow 眼睛材质 Emission Strength 提到 3.0 (黑暗设施里发光大眼),
             全套动画原样保留。
    2. 太空基地 / 万圣节 cherry-pick 道具 -> assets/static/vendor/{space,halloween}/*.glb
       原样转自包含 GLB (贴图内嵌, 白+红科幻风本身就很 LC, 不改色)。
"""

import os
import bpy
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENDOR = os.path.join(ROOT, "assets", "vendor", "kaykit")
DYN_DIR = os.path.join(ROOT, "assets", "dynamic")
STATIC_VENDOR = os.path.join(ROOT, "assets", "static", "vendor")

SKEL_DIR = os.path.join(VENDOR, "KayKit-Character-Pack-Skeletons-1.0",
                        "addons", "kaykit_character_pack_skeletons", "Characters", "gltf")
SPACE_DIR = os.path.join(VENDOR, "KayKit-Space-Base-Bits-1.0",
                         "addons", "kaykit_space_base_bits", "Assets", "gltf")
HALLOW_DIR = os.path.join(VENDOR, "KayKit-Halloween-Bits-1.0",
                          "addons", "kaykit_halloween_bits", "Assets", "gltf")

os.makedirs(DYN_DIR, exist_ok=True)

# LC 微调参数: 去饱和 + 冷调压暗 (直接烘进贴图像素, 引擎无关)
LC_SAT = 0.30
LC_TINT = (0.55, 0.58, 0.68)
GLOW_STRENGTH = 3.0


def filtered_gltf_export(filepath, **kwargs):
    props = bpy.ops.export_scene.gltf.get_rna_type().properties
    safe = {k: v for k, v in kwargs.items() if k in props}
    return bpy.ops.export_scene.gltf(filepath=filepath, **safe)


def bake_darken_image(img, sat, tint):
    """用 numpy 对贴图像素做 去饱和 + 乘色压暗。

    之前试过 Hue/Saturation 节点和 Mix(Multiply) 节点: 前者 glTF 不认,
    后者虽能导出 baseColorFactor, 但 Blender 重导入渲染时不完全生效, 预览不诚实。
    烘进像素后, 任何引擎/渲染路径看到的效果一致。
    """
    if not img or not img.size[0]:
        return False
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    rgb = px[:, :3]
    lum = (rgb * np.array([0.299, 0.587, 0.114], dtype=np.float32)).sum(axis=1, keepdims=True)
    desat = lum + (rgb - lum) * sat
    px[:, :3] = np.clip(desat * np.array(tint, dtype=np.float32), 0.0, 1.0)
    img.pixels.foreach_set(px.ravel())
    img.update()
    if not img.packed_file:
        img.pack()
    return True


def darken_material(mat, sat, tint):
    """找到材质里的贴图节点, 对其图像烘像素级压暗。"""
    if not mat.use_nodes:
        return False
    done = False
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeTexImage" and n.image:
            done |= bake_darken_image(n.image, sat, tint)
    return done


def boost_glow(mat, strength):
    if not mat.use_nodes:
        return
    for n in mat.node_tree.nodes:
        if n.bl_idname == "ShaderNodeBsdfPrincipled":
            n.inputs["Emission Strength"].default_value = strength


def curate_skeleton(glb_name, out_name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(SKEL_DIR, glb_name))
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
    print("CURATED_SKEL ->", out)


def curate_prop(src_dir, name, out_subdir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(src_dir, name))
    out_dir = os.path.join(STATIC_VENDOR, out_subdir)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, os.path.splitext(name)[0] + ".glb")
    filtered_gltf_export(
        out,
        export_format="GLB",
        export_yup=True,
        export_apply=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print("CURATED_PROP ->", out)


SKELETONS = [
    ("Skeleton_Minion.glb", "monster_skeleton_minion.glb"),
    ("Skeleton_Warrior.glb", "monster_skeleton_warrior.glb"),
    ("Skeleton_Rogue.glb", "monster_skeleton_rogue.glb"),
    ("Skeleton_Mage.glb", "monster_skeleton_mage.glb"),
]

SPACE_PICKS = [
    "basemodule_A.gltf", "basemodule_garage.gltf", "cargodepot_A.gltf",
    "containers_A.gltf", "drill_structure.gltf", "spacetruck.gltf",
    "lander_A.gltf", "landingpad_large.gltf", "tunnel_straight_A.gltf",
    "windturbine_tall.gltf", "solarpanel.gltf", "structure_tall.gltf",
]

HALLOW_PICKS = [
    "coffin.gltf", "gravestone.gltf", "gravemarker_A.gltf",
    "lantern_standing.gltf", "pumpkin_orange_jackolantern.gltf", "bone_A.gltf",
]

if __name__ == "__main__":
    for glb, out in SKELETONS:
        curate_skeleton(glb, out)
    for name in SPACE_PICKS:
        curate_prop(SPACE_DIR, name, "space")
    for name in HALLOW_PICKS:
        curate_prop(HALLOW_DIR, name, "halloween")
    print("VENDOR_LC_DONE")
