"""中式渐进 · 生灵级: 僵尸(jiangshi) 骨骼挂件四件。

不做人形、不做绑定、不做动画 —— 只做四件"挂到 KayKit 骷髅骨骼上"的中式配件,
由 game/scripts/chinese_jiangshi.gd 用 BoneAttachment3D 挂到 head/chest/hips 骨上。
这是本轮 ROI 的关键: 零绑定零动画投入, 换一个辨识度极高的中式敌人。

  jiangshi_hat       清式顶戴 (黑缎帽筒 + 帽檐 + 红顶珠), 原点=帽檐底面中心, 往下贴头骨
  jiangshi_talisman  额前黄符 (黄纸 + 朱砂符纹),           原点=纸片中心
  jiangshi_buzi      胸背方补 (靛蓝补子 + 金边框 + 金兽纹), 原点=补子中心
  jiangshi_coins     腰间铜钱串 (4 枚铜钱 + 串绳),         原点=最上一枚, 向下垂

坐标: z-up, "正面"= -Y (与 KayKit 骨骼 toes 方向一致, 见 inspect_rig)。
经 export_yup 后在 Godot 里: -Y(blender) -> +Z(godot) = 模型正面, +Z(blender) -> +Y = 上。

!! 尺寸依据 (坑28): KayKit 骨骼 rest 位置 (head z=1.24) 远小于蒙皮网格 —— 实测
Skeleton_Minion 蒙皮后: 头骨 z 1.264-2.132 (0.87m 高!), 脸面 y=-0.41, 身体 y=-0.34,
斗篷 y=-0.36, 腿前 y=-0.23。挂件必须按蒙皮网格定尺寸/偏移, 按骨骼点位定会整体
埋进模型 (首轮四件埋三件, 只有落进两腿缝隙的铜钱串露出来)。
挂接偏移 (对骨骼点, 与 chinese_jiangshi.gd SPECS 一致):
  hat      head  +0.81 (帽檐底 z=2.05, 骑在头顶 2.13 略沉)   fwd 0
  talisman head  +0.60 (符中心 z=1.84, 垂在眼(1.53-1.66)上方) fwd 0.40 (脸前)
  buzi     chest +0.03 (补子中心 z=1.00)                    fwd 0.371 (斗篷面外)
  coins    hips  +0.194 (顶钱 z=0.60, 腰带下)               fwd 0.24 (腿隙)

运行: blender --background --python tools/blender/build_chinese_jiangshi.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PI = math.pi


def extra_materials():
    """僵尸挂件专用材质 (refresh_materials 之后调用)。"""
    g = zh.__dict__
    g["M_SILK"] = zh.make_material("M_ZH_SilkBlack", (0.09, 0.09, 0.11), rough=0.5)
    g["M_INDIGO"] = zh.make_material("M_ZH_Indigo", (0.13, 0.18, 0.34), rough=0.75)
    g["M_TALIS"] = zh.make_material("M_ZH_Talisman", (0.90, 0.79, 0.32), rough=0.85)
    g["M_CINNABAR"] = zh.make_material("M_ZH_Cinnabar", (0.74, 0.11, 0.07), rough=0.7)
    g["M_COIN"] = zh.make_material("M_ZH_Coin", (0.74, 0.58, 0.24),
                                   rough=0.32, metal=0.85)
    g["M_CORD"] = zh.make_material("M_ZH_Cord", (0.30, 0.10, 0.08), rough=0.9)


# ---------------------------------------------------------------- 清式顶戴
SCALE_HAT = 1.9      # 头骨宽 0.88, 0.31 的帽檐会变成"顶针"
SCALE_TALISMAN = 2.2
SCALE_BUZI = 1.7
SCALE_COINS = 1.4


def build_jiangshi_hat():
    """清式顶戴: 黑缎帽檐 + 帽筒 + 珠座 + 红顶珠。

    原点 = 帽檐底面中心 (挂到 head 骨后再 -Y 方向无需偏移, 只需沿骨轴抬起)。
    H ≈ 0.158, 帽檐直径 0.31。
    """
    parts = [
        # 帽檐 (扁圆盘)
        zh.cyl("JS_H_Brim", 0.155, 0.014, (0, 0, 0.007), zh.M_SILK, verts=24),
        # 帽筒 (上收的圆台)
        zh.cone("JS_H_Dome", 0.098, 0.092, (0, 0, 0.060), zh.M_SILK,
                verts=24, r_top=0.074),
        # 帽筒顶盖 + 珠座 + 红顶珠
        zh.cyl("JS_H_Cap", 0.076, 0.008, (0, 0, 0.110), zh.M_SILK, verts=20),
        zh.cyl("JS_H_Seat", 0.030, 0.014, (0, 0, 0.121), zh.M_GOLD, verts=16),
        zh.sph("JS_H_Bead", 0.027, (0, 0, 0.142), zh.M_CINNABAR, seg=12, ring=8),
    ]
    obj = zh.join(parts, "jiangshi_hat")
    obj.scale = tuple(c * SCALE_HAT for c in obj.scale)  # 乘勿覆盖, join 后局部空间含 parts[0] 缩放
    return obj


# ---------------------------------------------------------------- 额前黄符
def build_jiangshi_talisman():
    """额前黄符: 竖长黄纸 + 朱砂符纹 (一道竖笔 + 三道横笔)。

    尺寸 0.058(x) x 0.005(y) x 0.150(z), 原点=纸片中心。
    符纹刻在 -Y 面 (正面), 凸出 1.5mm —— 低于坑16 的 12mm 门槛但这是"贴在纸上"的
    印刷纹, 近距离才看, 不靠它撑轮廓。
    """
    parts = [
        zh.box("JS_T_Paper", (0.058, 0.005, 0.150), (0, 0, 0), zh.M_TALIS),
        # 一道竖笔 (贯穿)
        zh.box("JS_T_StrokeV", (0.007, 0.003, 0.112), (0, -0.0045, 0.004),
               zh.M_CINNABAR),
        # 三道横笔
        zh.box("JS_T_Stroke1", (0.036, 0.003, 0.007), (0, -0.0045, 0.048),
               zh.M_CINNABAR),
        zh.box("JS_T_Stroke2", (0.040, 0.003, 0.007), (0, -0.0045, 0.004),
               zh.M_CINNABAR),
        zh.box("JS_T_Stroke3", (0.030, 0.003, 0.007), (0, -0.0045, -0.040),
               zh.M_CINNABAR),
        # 顶部小尖 (黄符对折的尖角)
        zh.cone("JS_T_Tip", 0.029, 0.018, (0, 0, 0.084), zh.M_TALIS,
                verts=4, r_top=0.0),
    ]
    obj = zh.join(parts, "jiangshi_talisman")
    obj.scale = tuple(c * SCALE_TALISMAN for c in obj.scale)  # 乘勿覆盖, join 后局部空间含 parts[0] 缩放
    return obj


# ---------------------------------------------------------------- 胸背方补
def build_jiangshi_buzi():
    """胸背方补: 靛蓝底 + 金边框 + 中心金兽纹(抽象)。

    尺寸 0.176 x 0.010 x 0.176, 原点=中心。挂到 chest 骨后沿正面法线推出去。
    """
    parts = [
        zh.box("JS_B_Plate", (0.170, 0.008, 0.170), (0, 0, 0), zh.M_INDIGO),
        # 金边: 上下 + 左右 (贴在 -Y 正面)
        zh.box("JS_B_EdgeT", (0.176, 0.004, 0.012), (0, -0.006, 0.079), zh.M_GOLD),
        zh.box("JS_B_EdgeB", (0.176, 0.004, 0.012), (0, -0.006, -0.079), zh.M_GOLD),
        zh.box("JS_B_EdgeL", (0.012, 0.004, 0.176), (-0.079, -0.006, 0), zh.M_GOLD),
        zh.box("JS_B_EdgeR", (0.012, 0.004, 0.176), (0.079, -0.006, 0), zh.M_GOLD),
        # 中心兽纹 (抽象: 圆身 + 四足)
        zh.cyl("JS_B_Body", 0.030, 0.005, (0, -0.008, 0.006), zh.M_GOLD,
               verts=16, rot=(0, PI / 2, 0)),
        zh.box("JS_B_LegFL", (0.010, 0.004, 0.030), (-0.028, -0.008, 0.030),
               zh.M_GOLD),
        zh.box("JS_B_LegFR", (0.010, 0.004, 0.030), (0.028, -0.008, 0.030),
               zh.M_GOLD),
        zh.box("JS_B_LegBL", (0.010, 0.004, 0.030), (-0.028, -0.008, -0.024),
               zh.M_GOLD),
        zh.box("JS_B_LegBR", (0.010, 0.004, 0.030), (0.028, -0.008, -0.024),
               zh.M_GOLD),
        # 下方海水江崖 (三道波浪)
        zh.box("JS_B_Wave1", (0.120, 0.004, 0.008), (0, -0.008, -0.058), zh.M_GOLD),
        zh.box("JS_B_Wave2", (0.090, 0.004, 0.008), (0, -0.008, -0.048), zh.M_GOLD),
    ]
    obj = zh.join(parts, "jiangshi_buzi")
    obj.scale = tuple(c * SCALE_BUZI for c in obj.scale)  # 乘勿覆盖, join 后局部空间含 parts[0] 缩放
    return obj


# ---------------------------------------------------------------- 腰间铜钱串
def build_jiangshi_coins():
    """腰间铜钱串: 4 枚外圆内方铜钱 + 串绳, 从原点向下垂 0.20。

    torus 默认 rot=(PI/2,0,0) -> 环在 XZ 竖直面, 轴=Y(正面法线) -> 钱面朝前。
    """
    parts = [
        zh.box("JS_C_Cord", (0.005, 0.005, 0.215), (0, 0, -0.100), zh.M_CORD),
    ]
    for i in range(4):
        z = -0.020 - i * 0.058
        parts.append(zh.torus("JS_C_Coin%d" % i, 0.030, 0.0075, (0, 0, z),
                              zh.M_COIN, rot=(PI / 2, 0, 0)))
    obj = zh.join(parts, "jiangshi_coins")
    obj.scale = tuple(c * SCALE_COINS for c in obj.scale)  # 乘勿覆盖, join 后局部空间含 parts[0] 缩放
    return obj


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("jiangshi_hat", build_jiangshi_hat),
        ("jiangshi_talisman", build_jiangshi_talisman),
        ("jiangshi_buzi", build_jiangshi_buzi),
        ("jiangshi_coins", build_jiangshi_coins),
    ]
    for name, fn in builders:
        zh.refresh_materials()
        extra_materials()
        zh.delete_all()
        obj = fn()
        path = os.path.join(OUT, name + ".glb")
        filtered_gltf_export(
            path, export_format="GLB", export_yup=True, export_apply=False,
            export_materials="EXPORT", export_cameras=False, export_lights=False,
        )
        print("ZHJIANGSHI ->", path, "verts=", len(obj.data.vertices))
    print("ZHJIANGSHI_DONE")


main()
