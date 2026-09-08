"""中式旧物废料线预览 (微距, 四件一排)。"""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)
ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")

bpy.ops.wm.read_factory_settings(use_empty=True)
x = 0.0
for name in ["thermos_bottle", "enamel_mug", "tin_can", "ration_bundle"]:
    import_gltf(os.path.join(ZH, name + ".glb"))
    for o in bpy.context.selected_objects:
        o.location.x += x
    x += 0.35
add_ground(size=8)
setup_scene()
for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
    lt.data.energy *= 0.48
add_camera("Cam", (0.62, -0.72, 0.5), (0.52, 0, 0.14), 32.0)
render_to("zh_relics_line.png")
print("ZHRELIC_PV_DONE")
