"""一次性: 列出设施 GLB 中 x∈[9..15], y∈[2..7] 的物体, 排查走廊视线遮挡。"""
import bpy, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import import_gltf, ROOT

bpy.ops.wm.read_factory_settings(use_empty=True)
objs = import_gltf(os.path.join(ROOT, "assets", "maps", "vendor", "facility_three_zone.glb"))
bpy.context.view_layer.update()
for o in objs:
    if o.type != "MESH":
        continue
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    xmn = min(p.x for p in pts); xmx = max(p.x for p in pts)
    ymn = min(p.y for p in pts); ymx = max(p.y for p in pts)
    zmx = max(p.z for p in pts)
    if xmx > 8.5 and xmn < 15.5 and ymx > 1.5 and ymn < 7.5:
        print(f"{o.name:28s} x[{xmn:6.2f},{xmx:6.2f}] y[{ymn:6.2f},{ymx:6.2f}] zmax={zmx:5.2f}")
