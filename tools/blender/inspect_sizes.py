"""一次性: 实测收编件 bbox 尺寸, 供设施布局用。"""
import bpy, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import import_gltf, ROOT

SV = os.path.join(ROOT, "assets", "static", "vendor")
PIECES = [
    ("dungeon", "wall"), ("dungeon", "floor_tile_large"),
    ("dungeon", "floor_tile_grate"), ("dungeon", "wall_doorway"),
    ("dungeon", "wall_gated"), ("dungeon", "wall_window_closed"),
    ("dungeon", "pillar"), ("dungeon", "wall_broken"),
    ("backrooms", "wall"), ("backrooms", "floor_dirt_large"),
]
for sub, name in PIECES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    objs = import_gltf(os.path.join(SV, sub, name + ".glb"))
    bpy.context.view_layer.update()
    pts = []
    for o in objs:
        if o.type == "MESH":
            pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
    if not pts:
        print(f"{sub}/{name}: NO MESH")
        continue
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = mx - mn
    print(f"{sub}/{name:22s} size=({s.x:5.2f},{s.y:5.2f},{s.z:5.2f}) zmin={mn.z:5.2f}")
