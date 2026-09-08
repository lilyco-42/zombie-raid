"""中式旧物废料线第三批预览 (微距, 四件一排 + 四件单独特写)。

本批 build 已把"正面"统一建在 -Y 侧, 与默认镜头同侧, 无需再转 180°。
"""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)
ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PIECES = [("abacus", 0.0), ("kerosene_lamp", 0.34),
          ("enamel_spittoon", 0.62), ("gramophone", 0.86)]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    add_ground(size=8)
    setup_scene()
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bg = bpy.data.worlds["World"].node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Strength"].default_value = 0.45
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.30


# 1) 四件一排 (全貌)
reset()
for name, x in PIECES:
    objs = import_gltf(os.path.join(ZH, name + ".glb"))
    for o in objs:
        o.location.x += x
add_camera("Cam", (0.44, -1.05, 0.46), (0.44, 0, 0.09), 26.0)
render_to("zh_relics3_line.png")

# 2) 四件特写
CAMS = {
    "abacus":          ((0.0, -0.20, 0.32), (0.0, 0.0, 0.014), 32.0),
    "kerosene_lamp":   ((0.0, -0.32, 0.20), (0.0, 0.0, 0.120), 32.0),
    "enamel_spittoon": ((0.0, -0.42, 0.34), (0.0, 0.0, 0.080), 32.0),
    "gramophone":      ((0.02, -0.42, 0.22), (0.02, 0.0, 0.110), 28.0),
}
for name, _ in PIECES:
    reset()
    import_gltf(os.path.join(ZH, name + ".glb"))
    loc, tgt, fov = CAMS[name]
    add_camera("Cam", loc, tgt, fov)
    render_to("zh_relics3_" + name + ".png")
print("ZHRELIC3_PV_DONE")
