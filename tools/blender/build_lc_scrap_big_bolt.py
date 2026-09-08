"""致命公司(LC)风格 · 道具/废料 — 大螺栓 scrap_big_bolt。
LC 资产循环 第1件 (道具类): 低模锈铁, 拾取废料, 玩法用途=收集配额。
做法: 六棱头(verts=6) + 螺杆 + 三道螺纹环 + 收尾锥, 全基础几何, 几十顶点。
风格基线: KayKit 低模 + 破旧工业锈铁。
产出: assets/dynamic/scrap_big_bolt.glb + assets/_previews/lc_scrap_big_bolt.png
运行: blender --background --python tools/blender/build_lc_scrap_big_bolt.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import filtered_gltf_export, ROOT
from render_vendor_previews import setup_scene, add_camera, add_ground, render_to

OUT = os.path.join(ROOT, "assets", "dynamic")
PREV = os.path.join(ROOT, "assets", "_previews")


def mat(name, rgb, rough=0.7, metal=0.4):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def cyl(name, r, depth, loc, m, verts=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts,
                                        location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(m)
    return o


def cone(name, r, depth, loc, m, verts=12, r_top=0.0):
    bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r_top, depth=depth,
                                    vertices=verts, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(m)
    return o


def join(parts, name):
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    parts[0].name = name
    return parts[0]


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M_RUST = mat("M_LC_Rust", (0.46, 0.30, 0.17), rough=0.62, metal=0.5)
    M_RUST_D = mat("M_LC_RustDark", (0.30, 0.25, 0.20), rough=0.70, metal=0.45)
    parts = [
        cyl("Bolt_Head", 0.55, 0.40, (0, 0, 0.20), M_RUST_D, verts=6),
        cyl("Bolt_Shaft", 0.24, 0.75, (0, 0, 0.775), M_RUST, verts=12),
        cyl("Bolt_Thread1", 0.28, 0.06, (0, 0, 0.55), M_RUST_D, verts=12),
        cyl("Bolt_Thread2", 0.28, 0.06, (0, 0, 0.72), M_RUST_D, verts=12),
        cyl("Bolt_Thread3", 0.28, 0.06, (0, 0, 0.89), M_RUST_D, verts=12),
        cone("Bolt_Tip", 0.24, 0.12, (0, 0, 1.19), M_RUST, verts=12, r_top=0.08),
    ]
    obj = join(parts, "scrap_big_bolt")

    os.makedirs(OUT, exist_ok=True)
    glb = os.path.join(OUT, "scrap_big_bolt.glb")
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    filtered_gltf_export(
        glb, export_format="GLB", export_yup=True, export_apply=False,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
        use_selection=True,
    )
    print("LC_SCRAP ->", glb, "verts=", len(obj.data.vertices))

    # 预览 (场景内直接渲, 不重导)
    add_ground(size=60)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.5
    add_camera("Cam", (2.6, -4.2, 2.2), (0, 0, 0.7), lens=40.0)
    os.makedirs(PREV, exist_ok=True)
    render_to(os.path.join(PREV, "lc_scrap_big_bolt.png"))
    print("LC_SCRAP_PV ->", os.path.join(PREV, "lc_scrap_big_bolt.png"))
    print("LC_SCRAP_DONE")


main()
