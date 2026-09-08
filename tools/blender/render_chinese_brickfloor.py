"""中式渐进 · 青砖铺地 目检 (2x2 格拼接 + 近景砖缝)。

目检要点:
  1) 2x2 拼接后是否**无缝连续** (这是本件的全部意义: 补掉 CELL=6 的 2m 空洞)
  2) 错缝是否成立 (奇偶行错半砖, 边缘半砖补齐)
  3) 近景砖缝阴影是否有层次 (lyco 坑16: 凸出 < 12mm 远观看不出, 这里 20mm)
"""
import bpy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)
ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
TILE = 6.0


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    add_ground(size=40, z=-0.05)
    setup_scene()
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bg = bpy.data.worlds["World"].node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Strength"].default_value = 0.5
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.30


def lay_grid(n=2, step=None):
    """铺 n x n 块, 中心在原点。"""
    step = step or TILE
    half = (n - 1) * step * 0.5
    for i in range(n):
        for j in range(n):
            for o in import_gltf(os.path.join(ZH, "brick_pave_6m.glb")):
                o.location.x += i * step - half
                o.location.y += j * step - half
                o.location.z += 0.01


# 1) 俯瞰: 检查 2x2 拼接无缝
reset()
lay_grid(2)
add_camera("Cam", (0.0, 0.0, 13.0), (0.0, 0.0, 0.0), 45.0)
render_to("zh_brickfloor_top.png")

# 2) 斜视: 砖缝立体感 + 错缝
reset()
lay_grid(2)
add_camera("Cam", (7.5, -8.5, 6.2), (0.0, 0.0, 0.0), 38.0)
render_to("zh_brickfloor_angle.png")

# 3) 近景: 砖缝阴影层次 (略抬高机位, 避免掠射角把深色 albedo 提亮失真)
reset()
lay_grid(2)
add_camera("Cam", (1.6, -2.8, 1.5), (0.0, 0.8, 0.02), 40.0)
render_to("zh_brickfloor_close.png")
print("ZHBRICK_PV_DONE")
