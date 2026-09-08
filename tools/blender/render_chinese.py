"""中式 Phase 1 资产预览: 结构大件一排 + 桌面小件近景。"""
import bpy, os, sys
import mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)

SRC = os.path.join(ROOT, "assets", "static", "vendor", "chinese")


def world_bbox(objs):
    pts = []
    for o in objs:
        if o.type == "MESH":
            for c in o.bound_box:
                pts.append(o.matrix_world @ mathutils.Vector(c))
    lo = mathutils.Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = mathutils.Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def place_row(names, spacing):
    """按名字依次导入并排开, 底面中心对齐 (i*spacing, 0, 0), 返回总宽中心 x。"""
    roots_all = []
    for i, nm in enumerate(names):
        objs = import_gltf(os.path.join(SRC, nm + ".glb"))
        roots = [o for o in objs if o.parent is None or o.parent not in objs]
        lo, hi = world_bbox(objs)
        dx = i * spacing - (lo.x + hi.x) / 2
        dy = 0 - (lo.y + hi.y) / 2
        dz = 0 - lo.z
        for r in roots:
            r.location.x += dx
            r.location.y += dy
            r.location.z += dz
        roots_all.extend(roots)
        print("ZH_PV", nm, "->", i * spacing)
    return (len(names) - 1) * spacing / 2


def shot(out_name, cam_loc, target, lens, light_mult=0.45):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    add_ground(size=60)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, target, lens=lens)
    render_to(out_name)


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    add_ground(size=60)
    cx = place_row(["roller_door", "slogan_safety", "slogan_tunnel", "stone_lion"], 4.5)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.35
    add_camera("Cam", (cx + 9.0, -14.0, 12.0), (cx, 0, 0.8), lens=28)
    render_to("zh_structures.png")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    add_ground(size=60)
    cx2 = place_row(["lantern_red", "lantern_red", "enamel_set"], 1.1)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.45
    add_camera("Cam", (cx2 + 0.4, -3.4, 1.5), (cx2, 0, 0.45), lens=40)
    render_to("zh_props.png")
    print("ZH_PV_DONE")
