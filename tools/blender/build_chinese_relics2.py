"""中式旧物 · 废料线第二批 (参数化小器物, lyco 例外条款允许自建)。

  old_letter  家书     (航空信封+信纸半抽+红蓝斜条+邮票+红印, H≈0.02)
  work_badge  工牌     (硬卡+蓝挂绳+金属夹+照片框+红编号条, H≈0.16)
  half_jade   半玉佩   (扁玉环沿直径断开取一半+金挂环, H≈0.02)
  old_radio   老收音机 (木壳+喇叭格栅+刻度盘+双旋钮+斜天线, H≈0.33)

真实比例 (拾取件), 原点=底面中心, z-up。
运行: blender --background --python tools/blender/build_chinese_relics2.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PI = math.pi


def extra_materials():
    """第一批已有 M_PAPER/M_BAMBOO/M_BAMBOO_D, 这里补第二批专属材质。"""
    g = zh.__dict__
    g["M_PAPER"] = zh.make_material("M_ZH_Paper", (0.82, 0.76, 0.62), rough=0.9)
    g["M_BAMBOO"] = zh.make_material("M_ZH_Bamboo", (0.52, 0.41, 0.24), rough=0.85)
    g["M_BAMBOO_D"] = zh.make_material("M_ZH_BambooDark", (0.36, 0.28, 0.16), rough=0.9)
    g["M_JADE"] = zh.make_material("M_ZH_Jade", (0.42, 0.70, 0.56), rough=0.18)
    g["M_INK"] = zh.make_material("M_ZH_Ink", (0.26, 0.27, 0.30), rough=0.6)


def bisect_half(obj, plane_no=(0, 1, 0), clear_inner=True):
    """沿过物体原点的平面切开并丢弃一半 (半玉佩的断口)。

    先归零 location 再切 —— bisect 的 plane_co 走物体局部空间,
    带偏移容易切歪。切完由调用方重新定位。
    """
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bisect(plane_co=(0.0, 0.0, 0.0), plane_no=plane_no,
                        clear_inner=clear_inner, clear_outer=not clear_inner,
                        use_fill=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


# ---------------------------------------------------------------- 家书
def build_old_letter():
    """家书: 米黄信封 + 半抽出的信纸 + 航空红蓝斜条 + 邮票 + 红印章。

    全部装饰件 (斜条/邮票/印章/文字) z 凸出到 0.014-0.018 范围,
    微距图能看清; 主体信封 z=0.008 作"衬底"用。
    """
    parts = [
        zh.box("OL_Envelope", (0.165, 0.105, 0.008), (0, 0, 0.004), zh.M_PAPER),
        # 半抽出的信纸 (错开+微旋, 压在信封上)
        zh.box("OL_Sheet", (0.140, 0.088, 0.003), (0.014, 0.010, 0.015),
               zh.M_BOARD_W, rot=(0, 0, 0.13)),
        zh.box("OL_Line1", (0.090, 0.004, 0.001), (0.030, 0.030, 0.018),
               zh.M_INK, rot=(0, 0, 0.13)),
        zh.box("OL_Line2", (0.090, 0.004, 0.001), (0.028, 0.018, 0.018),
               zh.M_INK, rot=(0, 0, 0.13)),
        zh.box("OL_Line3", (0.055, 0.004, 0.001), (0.014, 0.006, 0.018),
               zh.M_INK, rot=(0, 0, 0.13)),
        # 封舌
        zh.box("OL_Flap", (0.150, 0.048, 0.002), (0, -0.028, 0.013), zh.M_PAPER),
        # 航空信封红蓝斜条 (上缘 4 道, z 凸出 0.015)
        zh.box("OL_Air1", (0.018, 0.004, 0.001), (-0.062, 0.046, 0.015),
               zh.M_TXT_R, rot=(0, 0, 0.7)),
        zh.box("OL_Air2", (0.018, 0.004, 0.001), (-0.042, 0.046, 0.015),
               zh.M_EBLUE, rot=(0, 0, 0.7)),
        zh.box("OL_Air3", (0.018, 0.004, 0.001), (-0.022, 0.046, 0.015),
               zh.M_TXT_R, rot=(0, 0, 0.7)),
        zh.box("OL_Air4", (0.018, 0.004, 0.001), (-0.002, 0.046, 0.015),
               zh.M_EBLUE, rot=(0, 0, 0.7)),
        # 邮票
        zh.box("OL_Stamp", (0.026, 0.021, 0.003), (0.062, 0.036, 0.016), zh.M_EBLUE),
        # 红印章
        zh.box("OL_Seal", (0.018, 0.018, 0.003), (-0.058, -0.032, 0.016), zh.M_RED),
    ]
    return zh.join(parts, "old_letter")


# ---------------------------------------------------------------- 工牌
def build_work_badge():
    """工牌: 蓝挂绳 + 金属夹 + 白硬卡(蓝头/照片框/文字条/红编号)。"""
    parts = [
        # 卡身竖立, 卡面朝 +Y
        zh.box("WB_Card", (0.058, 0.004, 0.085), (0, 0, 0.0575), zh.M_BOARD_W),
        # 蓝 header
        zh.box("WB_Head", (0.058, 0.001, 0.020), (0, 0.0032, 0.0865), zh.M_EBLUE),
        # 照片框 + 两条文字
        zh.box("WB_Photo", (0.024, 0.001, 0.030), (-0.013, 0.0032, 0.052), zh.M_INK),
        zh.box("WB_Txt1", (0.020, 0.001, 0.005), (0.012, 0.0032, 0.058), zh.M_STONE_D),
        zh.box("WB_Txt2", (0.016, 0.001, 0.005), (0.010, 0.0032, 0.048), zh.M_STONE_D),
        # 红色编号条
        zh.box("WB_No", (0.032, 0.001, 0.006), (0, 0.0032, 0.030), zh.M_TXT_R),
        # 金属夹
        zh.box("WB_Clip", (0.014, 0.008, 0.012), (0, 0, 0.102), zh.M_ALU),
        # 挂绳 (倒 V, 绕 Y 轴外撇)
        zh.box("WB_CordL", (0.005, 0.004, 0.062), (-0.016, 0, 0.130),
               zh.M_EBLUE, rot=(0, 0.42, 0)),
        zh.box("WB_CordR", (0.005, 0.004, 0.062), (0.016, 0, 0.130),
               zh.M_EBLUE, rot=(0, -0.42, 0)),
    ]
    return zh.join(parts, "work_badge")


# ---------------------------------------------------------------- 半玉佩
def build_half_jade():
    """半玉佩: 扁平玉环沿直径断开, 只留一半 + 金挂环 (一人一半的叙事件)。"""
    ring = zh.torus("HJ_Ring", 0.033, 0.0105, (0, 0, 0), zh.M_JADE, rot=(0, 0, 0))
    ring.scale = (1.0, 1.0, 0.55)  # 压扁成玉佩片
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ring
    ring.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bisect_half(ring, plane_no=(0, 1, 0), clear_inner=True)  # 保留一半
    ring.location = (0, 0, 0.007)
    # 金挂环 (竖立, 法线沿 Y), 在保留端的顶部
    hook = zh.torus("HJ_Hook", 0.008, 0.0022, (0, -0.040, 0.012), zh.M_GOLD)
    return zh.join([ring, hook], "half_jade")


# ---------------------------------------------------------------- 老收音机
def build_old_radio():
    """老收音机: 木壳 + 喇叭格栅(7道竖条) + 刻度盘+红指针 + 双旋钮 + 斜天线 + 顶提把。

    上轮教训: 前面板 y 凸出仅 0.064, 格栅/旋钮被自身面板盖住 → 远观如素盒。
    本轮改:
      - 前面板 y 推到 +0.078 (凸 18mm) 且 z 缩窄到 0.11, 让顶/底边留出深色木壳边框
      - 格栅 7 道竖条 y=+0.090 (凸 30mm, 远观清楚)
      - 刻度盘 y=+0.085, 内部下沉 0.003 形成凹槽
      - 双旋钮 y=+0.090, 半径 0.020, 厚 0.018
      - 旋钮白指示点 (不在红中心, 像收音机频率线)
    """
    parts = [
        # 木壳 (深木, M_BAMBOO_D 已在本批被覆盖为深色版)
        zh.box("OR_Body", (0.26, 0.12, 0.16), (0, 0, 0.08), zh.M_BAMBOO_D),
        # 前面板 (凸 18mm, 缩小顶/底/左/右 让深色木壳形成边框)
        zh.box("OR_Panel", (0.215, 0.018, 0.110), (0, 0.078, 0.082), zh.M_STONE_D),
        # 喇叭格栅 (左侧 7 道竖条, 凸 30mm)
        *[zh.box("OR_Grate%d" % i, (0.006, 0.012, 0.078),
                 (-0.090 + i * 0.012, 0.090, 0.082), zh.M_INK)
          for i in range(7)],
        # 刻度盘 (凸 25mm, z 高度 24mm 容纳刻度感)
        zh.box("OR_Dial", (0.078, 0.010, 0.024), (0.038, 0.085, 0.118), zh.M_BOARD_W),
        # 刻度盘内框 (深色凹槽)
        zh.box("OR_DialInk", (0.072, 0.001, 0.020), (0.038, 0.0905, 0.118), zh.M_INK),
        # 红指针
        zh.box("OR_Needle", (0.003, 0.001, 0.018), (0.026, 0.0905, 0.118), zh.M_RED),
        # 双旋钮 (M_RUST, 凸 30mm, 半径 0.020)
        zh.cyl("OR_Knob1", 0.020, 0.018, (0.030, 0.090, 0.060), zh.M_RUST,
               verts=16, rot=(PI / 2, 0, 0)),
        zh.cyl("OR_Knob2", 0.020, 0.018, (0.082, 0.090, 0.060), zh.M_RUST,
               verts=16, rot=(PI / 2, 0, 0)),
        # 旋钮白色频率指示点 (从中心向上 0.014 像老式收音机表针)
        zh.box("OR_K1Mark", (0.004, 0.002, 0.012), (0.030, 0.104, 0.060), zh.M_BOARD_W),
        zh.box("OR_K2Mark", (0.004, 0.002, 0.012), (0.082, 0.104, 0.060), zh.M_BOARD_W),
        # 顶提把
        zh.box("OR_Handle", (0.10, 0.014, 0.009), (0, 0, 0.168), zh.M_BAMBOO_D),
        # 斜天线 (绕 Y 轴外撇)
        zh.cyl("OR_Ant", 0.0035, 0.22, (0.108, -0.035, 0.215), zh.M_ALU,
               verts=8, rot=(0, 0.32, 0)),
    ]
    return zh.join(parts, "old_radio")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("old_letter", build_old_letter),
        ("work_badge", build_work_badge),
        ("half_jade", build_half_jade),
        ("old_radio", build_old_radio),
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
        print("ZHRELIC2 ->", path, "verts=", len(obj.data.vertices))
    print("ZHRELIC2_DONE")


main()
