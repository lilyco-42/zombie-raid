"""设施走廊拼接场景: 用第二批收编的地牢结构件拼一条 LC 风走廊。

模板导入 → 量 bbox → 链接复制摆位 → 删模板 → 导出 GLB。
所有件对齐方式: bbox 底面中心落到目标点 (z=0 为地板顶)。
"""
import bpy, os, sys, math
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import filtered_gltf_export, ROOT

DGN = os.path.join(ROOT, "assets", "static", "vendor", "dungeon")
OUT = os.path.join(ROOT, "assets", "maps", "vendor", "facility_corridor.glb")

TEMPLATES = {}  # name -> (empty, bbox_min, bbox_max, size)


def load_template(name, src_dir=None, key=None):
    """导入一件收编 GLB, 挂到空物体下当模板, 记录世界 bbox。key 可覆盖字典键名。"""
    src_dir = src_dir or DGN
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(src_dir, name + ".glb"))
    new = [o for o in bpy.data.objects if o not in before]
    empty = bpy.data.objects.new("TPL_" + name, None)
    bpy.context.collection.objects.link(empty)
    for o in new:
        if o.parent is None:
            o.parent = empty
    bpy.context.view_layer.update()
    pts = []
    for o in new:
        if o.type == "MESH":
            for corner in o.bound_box:
                pts.append(o.matrix_world @ Vector(corner))
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    TEMPLATES[key or name] = (empty, mn, mx, mx - mn)
    return empty, mn, mx, mx - mn


def place(name, x, y, z=0.0, rot_z=0.0, scale=1.0):
    """链接复制模板, 使副本 bbox 底面中心落在 (x,y,z)。"""
    tpl, mn, mx, size = TEMPLATES[name]
    root = tpl.copy()  # 空物体副本
    bpy.context.collection.objects.link(root)
    rel_bc = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z)) - tpl.location
    R = Matrix.Rotation(math.radians(rot_z), 4, "Z")
    root.rotation_euler.z = math.radians(rot_z)
    root.scale = (scale, scale, scale)
    root.location = Vector((x, y, z)) - (R @ rel_bc) * scale
    for child in tpl.children:
        c = child.copy()  # 共享 mesh 与材质
        bpy.context.collection.objects.link(c)
        c.parent = root
        c.matrix_parent_inverse = child.matrix_parent_inverse.copy()
        c.location = child.location
        c.rotation_euler = child.rotation_euler
        c.scale = child.scale
    return root


def delete_templates():
    for name, (tpl, *_rest) in TEMPLATES.items():
        for child in list(tpl.children):
            bpy.data.objects.remove(child, do_unlink=True)
        bpy.data.objects.remove(tpl, do_unlink=True)
    TEMPLATES.clear()


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)

    for n in ("floor_tile_large", "wall", "wall_arched", "wall_broken",
              "wall_doorway", "wall_gated", "pillar",
              "torch_lit", "candle_triple", "barrel_large",
              "crates_stacked", "chest", "rubble_large", "trunk_medium_A"):
        load_template(n)

    tile_s = TEMPLATES["floor_tile_large"][3]
    wall_s = TEMPLATES["wall"][3]
    tw = 2 * tile_s.x          # 走廊净宽 (2 块地砖)
    tl = 6 * tile_s.y          # 走廊长 (6 块地砖)
    thick = wall_s.y           # 墙厚 (默认沿 X 走向时 y 为厚度)

    # 地板 2×6
    for i in range(2):
        for j in range(6):
            place("floor_tile_large", (i + 0.5) * tile_s.x, (j + 0.5) * tile_s.y)

    # 两侧墙 (旋转 90° 沿 Y 走向), 节奏: 平墙/平墙/拱墙/平墙/破墙/平墙
    side = ["wall", "wall", "wall_arched", "wall", "wall_broken", "wall"]
    wl = wall_s.x              # 墙段长
    for k, wname in enumerate(side):
        yc = (k + 0.5) * wl
        place(wname, -thick / 2, yc, rot_z=90)
        place(wname, tw + thick / 2, yc, rot_z=-90)  # 装饰面朝走廊内

    # 两端: 近端铁闸门, 远端木门
    place("wall_gated", tw / 2, -thick / 2)
    place("wall_doorway", tw / 2, tl + thick / 2)

    # 四角门柱
    for px, py in ((0, 0), (tw, 0), (0, tl), (tw, tl)):
        place("pillar", px, py)

    # 火把交替贴墙, 蜡烛备用照明
    for k, yc in enumerate((2.0, 6.0, 10.0)):
        if k % 2 == 0:
            place("torch_lit", 0.6, yc)
        else:
            place("torch_lit", tw - 0.6, yc)
    place("candle_triple", tw / 2 + 0.9, tl - 1.0)

    # 道具: 入口木桶+货箱, 中部碎石半堵, 尽头宝箱+木箱
    place("barrel_large", 0.7, 1.0)
    place("crates_stacked", tw - 0.8, 1.8)
    place("rubble_large", tw / 2 + 0.3, tl * 0.55, scale=0.45)
    place("chest", tw / 2 - 0.9, tl - 0.9)
    place("trunk_medium_A", tw - 0.7, tl - 0.8)

    delete_templates()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    filtered_gltf_export(
        OUT, export_format="GLB", export_yup=True, export_apply=False,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
    )
    print("CORRIDOR ->", OUT)


if __name__ == "__main__":
    main()
