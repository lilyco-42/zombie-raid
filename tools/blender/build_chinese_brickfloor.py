"""中式渐进 · 青砖铺地 (设施最深层地面/顶面的砖石补缺)。

## 为什么做这个

dungeon_builder 用 CELL=6.0 的网格开凿设施, 但 KayKit dungeon 的
`floor_tile_large` / `floor_wood_large_dark` 实测只有 **4.0 x 4.0** (见
.workbuddy/tmp/glb_size2.py 量测), 每格只铺一块 -> 每条格边界留下 **2m 宽的
空洞**, 地板下方/顶面上方只有纯黑背景, 走廊看着像悬空栈道。

本件是一块 **6.0 x 6.0** 的青砖铺地砖, 正好铺满一整格 (CELL=6), 由
chinese_floor.gd 逐格落位在既有地砖之上, 既补掉空洞又给"最深层"换上中式皮肉。

## 几何 (Blender z-up, 原点=底面中心)

- 灰缝底座: 6.00 x 6.00 x 0.04 (深灰)
- 青砖: 0.70 x 0.325 x 0.02, 错缝 (奇偶行错半砖), 8 列 x 16 行 = 136 块
  - 偶数行 8 整砖; 奇数行 2 个半砖(0.35 宽)贴边 + 7 整砖
  - 三档青灰色随机(固定种子)分布, 避免"塑料平铺"感
- 总厚 0.06m: 落位时 y=0.05 -> 顶面 0.11, 比既有地砖顶面(0.08)高 3cm,
  既完全盖住旧砖又不会 z-fighting (lyco 坑: 共面必闪)

## 不自建清单自查

青砖铺地 = 平整铺装功能件 (lyco §1 例外条款: 平整地形盒), 无飞檐/斗拱/瓦作/
脊兽/隔扇/漏窗/藻井/亭廊塔桥/太湖石。

运行: blender --background --python tools/blender/build_chinese_brickfloor.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")

TILE = 6.0          # 与 dungeon_builder.CELL 一致
MORTAR_H = 0.04     # 灰缝底座厚
BRICK_H = 0.02      # 青砖厚 (凸出底座 2cm 形成砖缝阴影)
PITCH_X = 0.75      # 砖长 + 缝
PITCH_Y = 0.375     # 砖宽 + 缝
BRICK_X = 0.70      # 砖长
BRICK_Y = 0.325     # 砖宽
GAP = PITCH_X - BRICK_X   # 0.05 缝宽


def make_material(name, rgb, rough=0.95, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    return m


def box(name, size, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    o.data.materials.append(mat)
    return o


def _rand(seed: int) -> float:
    """确定性伪随机 (LCG), 保证每次构建色斑一致。"""
    x = (1103515245 * seed + 12345) & 0x7FFFFFFF
    return (x % 10000) / 10000.0


def build_tile():
    m_mortar = make_material("M_ZH_Mortar", (0.062, 0.068, 0.074), rough=1.0)
    # 青砖三档: 偏冷的深灰蓝, 是"青"而不是"灰" (做旧老砖, 压暗防 Filmic 过曝)
    m_bricks = [
        make_material("M_ZH_BrickA", (0.150, 0.172, 0.172)),
        make_material("M_ZH_BrickB", (0.105, 0.126, 0.132)),
        make_material("M_ZH_BrickC", (0.192, 0.208, 0.202)),
    ]

    objs = [box("BP_Mortar", (TILE, TILE, MORTAR_H), (0.0, 0.0, MORTAR_H * 0.5),
                m_mortar)]

    zc = MORTAR_H + BRICK_H * 0.5
    rows = int(round(TILE / PITCH_Y))          # 16
    cols = int(round(TILE / PITCH_X))          # 8
    n = 0
    for j in range(rows):
        y = -TILE * 0.5 + PITCH_Y * 0.5 + j * PITCH_Y
        if j % 2 == 0:
            # 整砖行
            for i in range(cols):
                x = -TILE * 0.5 + PITCH_X * 0.5 + i * PITCH_X
                objs.append(box("BP_B", (BRICK_X, BRICK_Y, BRICK_H), (x, y, zc),
                                m_bricks[int(_rand(n) * 3) % 3]))
                n += 1
        else:
            # 错缝行: 两端半砖 + 中间 7 整砖
            half = PITCH_X * 0.5 - GAP * 0.5   # 0.35
            for sgn in (-1.0, 1.0):
                x = sgn * (TILE * 0.5 - half * 0.5)
                objs.append(box("BP_B", (half, BRICK_Y, BRICK_H), (x, y, zc),
                                m_bricks[int(_rand(n) * 3) % 3]))
                n += 1
            for i in range(cols - 1):
                x = -TILE * 0.5 + PITCH_X + i * PITCH_X
                objs.append(box("BP_B", (BRICK_X, BRICK_Y, BRICK_H), (x, y, zc),
                                m_bricks[int(_rand(n) * 3) % 3]))
                n += 1

    # 合并成单个对象 -> Godot 侧每格只有 1 个 MeshInstance3D, 而不是 137 个
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    joined = bpy.context.active_object
    joined.name = "brick_pave_6m"
    print("ZHBRICK bricks=", n, " objects=", len(objs),
          " verts=", len(joined.data.vertices))
    return joined


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = build_tile()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(OUT, obj.name + ".glb")
    filtered_gltf_export(path, export_format="GLB", export_yup=True,
                         export_apply=False, export_materials="EXPORT",
                         export_cameras=False, export_lights=False,
                         use_selection=True)
    print("ZHBRICK ->", path, round(os.path.getsize(path) / 1024.0, 1), "KB")
    print("ZHBRICK_DONE")


main()
