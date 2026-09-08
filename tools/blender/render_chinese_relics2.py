"""中式旧物废料线第二批预览 (微距, 四件一排 + 四件单独特写)。"""
import bpy, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)
ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PIECES = [("old_letter", 0.0), ("work_badge", 0.30),
          ("half_jade", 0.52), ("old_radio", 0.74)]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    add_ground(size=8)
    setup_scene()
    # setup_scene 默认 view_transform="Standard"=AgX, 把 baseColor<0.2 的
    # 深色都拉亮成米色, 失真。改 Filmic 还原 sRGB 直读 -> 与 Godot 渲染一致
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
        # 收音机 build 把"前面板/格栅/旋钮/刻度盘"放在 +Y (远离 camera 的一侧),
        # 镜头在 -Y 朝 +Y 方向看 → 实际只看到 M_BAMBOO_D 木壳背面 → 素盒.
        # 渲染时绕 Z 转 180° 让"前面"朝相机.
        if name == "old_radio":
            o.rotation_euler = (0, 0, math.pi)
add_camera("Cam", (0.40, -1.20, 0.42), (0.40, 0, 0.12), 26.0)
render_to("zh_relics2_line.png")

# 2) 四件特写 (验证前板/红印/航空斜条/挂环等细节)
for name, _ in PIECES:
    reset()
    objs = import_gltf(os.path.join(ZH, name + ".glb"))
    # 各件看点不同, 镜头微调
    if name == "old_letter":
        add_camera("Cam", (0.0, -0.20, 0.12), (0.0, 0.0, 0.008), 30.0)
    elif name == "work_badge":
        add_camera("Cam", (0.0, -0.30, 0.10), (0.0, 0.0, 0.08), 26.0)
    elif name == "half_jade":
        add_camera("Cam", (0.0, -0.18, 0.10), (0.0, -0.02, 0.012), 30.0)
    elif name == "old_radio":
        # 收音机: 旋转 180° 让前面板朝 +Y, 镜头放在 +Y 朝 -Y 看
        for o in objs:
            o.rotation_euler = (0, 0, math.pi)
        add_camera("Cam", (0.0, 0.36, 0.18), (0.0, -0.02, 0.08), 28.0)
    render_to("zh_relics2_" + name + ".png")
print("ZHRELIC2_PV_DONE")
