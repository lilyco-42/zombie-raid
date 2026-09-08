"""BLACK SOULS 大地图预览: 俯瞰 + 城门朝圣路 + 长明茶会 + 后花园 4 机位。"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, ROOT)

GLB = os.path.join(ROOT, "assets", "maps", "vendor", "blacksous_map.glb")


def shot(out_name, cam_loc, cam_target, lens, light_mult):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_gltf(GLB)
    add_ground(size=180)
    setup_scene()
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= light_mult
    add_camera("Cam", cam_loc, cam_target, lens=lens)
    render_to(out_name)


if __name__ == "__main__":
    # 俯瞰: 五区全貌 (西林/北城/中央茶会/东南墓园/东园)
    shot("bs_map_aerial.png", (60, -70, 62), (8, 2, 0), 28.0, 0.42)
    # 朝圣路正对城门: 石狮 + 门墙红灯笼 + 穿门可见残壁标语
    shot("bs_map_gate.png", (12, 1.5, 2.2), (12, 17, 2.2), 32.0, 0.45)
    # 长明茶会近景: 长桌烛火 + 搪瓷缸 + 椅阵
    shot("bs_map_tea.png", (10, 9, 4.2), (1.5, -0.5, 0.6), 30.0, 0.50)
    # 后花园: 拱门石狮红灯笼 → 庄园废墟客厅
    shot("bs_map_garden.png", (36, -4, 4.5), (54, 16, 1.2), 28.0, 0.50)
    print("BS_MAP_PV_DONE")
