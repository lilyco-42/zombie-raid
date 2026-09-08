"""中式旧物 · 废料线第三批 (参数化小器物, lyco 例外条款允许自建)。

  abacus          算盘   (木框+中梁+9档+63算珠, 平放, H≈0.027)
  kerosene_lamp   煤油灯 (底座+油壶+铜灯头+调焰轮+葫芦玻璃罩+提梁, H≈0.23)
  enamel_spittoon 搪瓷痰盂 (白搪瓷鼓腹收腰+蓝箍+蓝口沿, H≈0.124)
  gramophone      留声机 (木座+唱盘+唱片+唱臂+金喇叭花, H≈0.22)

真实比例 (拾取件), 原点=底面中心, z-up。
正面一律朝 -Y (与渲染端默认镜头在 -Y 一致, 免去 relics2 那次 180° 修正)。

上轮教训沿用:
  - 坑16/19: 前面细节凸出 < 12mm 远观看不出 -> 本批细节凸出 >= 15mm
  - 坑18: 渲染镜头在 -Y, 所以"正面"建在 -Y 侧

运行: blender --background --python tools/blender/build_chinese_relics3.py
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_chinese as zh
from build_vendor_lc import filtered_gltf_export, ROOT

OUT = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
PI = math.pi


def extra_materials():
    """第二批专属材质 + 本批新增 (玻璃/油/搪瓷蓝)。"""
    g = zh.__dict__
    g["M_PAPER"] = zh.make_material("M_ZH_Paper", (0.82, 0.76, 0.62), rough=0.9)
    g["M_BAMBOO"] = zh.make_material("M_ZH_Bamboo", (0.55, 0.42, 0.24), rough=0.85)
    g["M_BAMBOO_D"] = zh.make_material("M_ZH_BambooDark", (0.33, 0.25, 0.15), rough=0.9)
    g["M_JADE"] = zh.make_material("M_ZH_Jade", (0.42, 0.70, 0.56), rough=0.18)
    g["M_INK"] = zh.make_material("M_ZH_Ink", (0.20, 0.21, 0.24), rough=0.6)
    # 本批新增
    g["M_OIL"] = zh.make_material("M_ZH_Oil", (0.86, 0.70, 0.30), rough=0.22)
    # 玻璃罩暖色发光 (Filmic 下要 strength >= 2.5 才出"灯"的语义)
    g["M_GLASSW"] = zh.make_emissive("M_ZH_GlassWarm", (1.0, 0.66, 0.28), 2.6)
    g["M_BRASS"] = zh.make_material("M_ZH_Brass", (0.72, 0.56, 0.22),
                                    rough=0.35, metal=0.75)


# ---------------------------------------------------------------- 算盘
def build_abacus():
    """算盘: 平放, 面朝上。深木框 + 中梁 + 9 根金属档 + 上二下五共 63 颗木算珠。

    尺寸: 0.260(x) x 0.140(y) x 0.027(z)
    中梁上移到 y=+0.022 -> 上档放 2 珠, 下档放 5 珠 (经典布局)。
    """
    parts = [
        # 木框: 上下长边 (沿 X) + 左右短边 (沿 Y)
        zh.box("AC_RailT", (0.260, 0.016, 0.027), (0, 0.062, 0.0135), zh.M_BAMBOO_D),
        zh.box("AC_RailB", (0.260, 0.016, 0.027), (0, -0.062, 0.0135), zh.M_BAMBOO_D),
        zh.box("AC_PostL", (0.018, 0.140, 0.027), (-0.121, 0, 0.0135), zh.M_BAMBOO_D),
        zh.box("AC_PostR", (0.018, 0.140, 0.027), (0.121, 0, 0.0135), zh.M_BAMBOO_D),
        # 中梁 (上移, 给下档腾出 5 珠空间)
        zh.box("AC_Beam", (0.226, 0.010, 0.024), (0, 0.022, 0.0135), zh.M_BAMBOO_D),
    ]
    # 9 根档 (沿 Y)
    for i in range(9):
        x = -0.096 + i * 0.024
        parts.append(zh.cyl("AC_Rod%d" % i, 0.0018, 0.112, (x, 0, 0.0135),
                            zh.M_ALU, verts=6, rot=(PI / 2, 0, 0)))
    # 算珠: 上二下五
    up_ys = (0.034, 0.047)
    dn_ys = (-0.045, -0.0315, -0.018, -0.0045, 0.009)
    for i in range(9):
        x = -0.096 + i * 0.024
        for j, y in enumerate(up_ys):
            parts.append(zh.sph("AC_U%d_%d" % (i, j), 0.0090, (x, y, 0.0135),
                                zh.M_BAMBOO, seg=8, ring=5, scale=(1.0, 0.66, 1.0)))
        for j, y in enumerate(dn_ys):
            parts.append(zh.sph("AC_D%d_%d" % (i, j), 0.0090, (x, y, 0.0135),
                                zh.M_BAMBOO, seg=8, ring=5, scale=(1.0, 0.66, 1.0)))
    return zh.join(parts, "abacus")


# ---------------------------------------------------------------- 煤油灯
def build_kerosene_lamp():
    """煤油灯(罩子灯): 铝底座 + 琥珀油壶 + 铜灯头 + 调焰轮 + 葫芦玻璃罩 + 提梁。

    H≈0.23。玻璃罩用 emissive 暖色, 在暗设施里自带"灯"的语义。
    """
    parts = [
        # 底座
        zh.cyl("KL_Base", 0.046, 0.016, (0, 0, 0.008), zh.M_ALU),
        zh.cyl("KL_Collar", 0.030, 0.010, (0, 0, 0.021), zh.M_BRASS),
        # 油壶 (扁球, 琥珀色煤油)
        zh.sph("KL_Tank", 0.042, (0, 0, 0.050), zh.M_OIL, seg=14, ring=8,
               scale=(1.0, 1.0, 0.60)),
        # 铜灯头 + 调焰轮
        zh.cyl("KL_Burner", 0.021, 0.030, (0, 0, 0.087), zh.M_BRASS),
        zh.cyl("KL_Wheel", 0.011, 0.009, (0.030, 0, 0.087), zh.M_BRASS,
               verts=12, rot=(0, PI / 2, 0)),
        # 玻璃罩 (葫芦形: 下鼓 + 上收, 衔接处缩 1mm 避 z-fight)
        zh.cone("KL_ChimA", 0.023, 0.046, (0, 0, 0.125), zh.M_GLASSW,
                verts=16, r_top=0.030),
        zh.cone("KL_ChimB", 0.030, 0.056, (0, 0, 0.176), zh.M_GLASSW,
                verts=16, r_top=0.020),
        # 顶盖 + 顶提环 (rot=(0,0,0) -> 水平环, 轴=Z, 贴在顶盖上)
        zh.cyl("KL_Cap", 0.024, 0.010, (0, 0, 0.209), zh.M_ALU),
        zh.torus("KL_Ring", 0.019, 0.0035, (0, 0, 0.218), zh.M_ALU,
                 rot=(0, 0, 0)),
        # 侧提环 (法线沿 X -> 环在 YZ 竖直面内), 小尺寸贴着灯头/油壶才像"长在灯上"
        zh.torus("KL_Bail", 0.028, 0.003, (0.036, 0, 0.090), zh.M_ALU,
                 rot=(0, PI / 2, 0)),
    ]
    return zh.join(parts, "kerosene_lamp")


# ---------------------------------------------------------------- 搪瓷痰盂
def build_enamel_spittoon():
    """搪瓷痰盂: 白搪瓷鼓腹 -> 收腰 -> 外撇口, 三道蓝箍 (腹/口沿/底圈)。

    H≈0.124, 口径 0.18。
    """
    parts = [
        zh.cone("ES_Body", 0.052, 0.070, (0, 0, 0.035), zh.M_ENAMEL,
                verts=20, r_top=0.100),
        zh.cone("ES_Waist", 0.100, 0.030, (0, 0, 0.085), zh.M_ENAMEL,
                verts=20, r_top=0.070),
        zh.cone("ES_Mouth", 0.070, 0.018, (0, 0, 0.109), zh.M_ENAMEL,
                verts=20, r_top=0.090),
        # 内膛 (深色, 做出"开口"的错觉) — 略低于口沿
        zh.cyl("ES_Hole", 0.084, 0.004, (0, 0, 0.1155), zh.M_INK, verts=20),
        # 三道蓝箍 (rot=(0,0,0) 让环轴=Z -> 环在 XY 水平面)
        zh.torus("ES_Foot", 0.052, 0.005, (0, 0, 0.006), zh.M_EBLUE,
                 rot=(0, 0, 0)),
        zh.torus("ES_Band", 0.1005, 0.0055, (0, 0, 0.070), zh.M_EBLUE,
                 rot=(0, 0, 0)),
        zh.torus("ES_Rim", 0.090, 0.006, (0, 0, 0.118), zh.M_EBLUE,
                 rot=(0, 0, 0)),
    ]
    return zh.join(parts, "enamel_spittoon")


# ---------------------------------------------------------------- 留声机
def build_gramophone():
    """留声机: 木座 + 四脚 + 唱盘/唱片/红标 + 唱臂 + 金色喇叭花 (开口朝 -Y 前上方)。

    H≈0.22。喇叭轴 = R_x(0.62) 作用于 +Z = (0, -0.581, 0.814) -> 朝前上方。
    """
    axis_tilt = 0.62
    feet = [zh.cyl("GP_Foot%d" % i, 0.011, 0.008, (sx * 0.068, sy * 0.058, 0.004),
                   zh.M_INK, verts=10)
            for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)])]
    parts = list(feet)
    parts += [
        zh.box("GP_Base", (0.170, 0.150, 0.048), (0, 0, 0.032), zh.M_BAMBOO_D),
        # 唱盘 / 唱片 / 红标签 / 中心轴
        zh.cyl("GP_Platter", 0.058, 0.008, (0, 0, 0.060), zh.M_INK, verts=24),
        zh.cyl("GP_Disc", 0.054, 0.003, (0, 0, 0.066), zh.M_INK, verts=24),
        zh.cyl("GP_Label", 0.019, 0.0015, (0, 0, 0.0685), zh.M_TXT_R, verts=20),
        zh.cyl("GP_Spindle", 0.0035, 0.020, (0, 0, 0.074), zh.M_ALU, verts=8),
        # 唱臂座 + 唱臂
        zh.cyl("GP_ArmBase", 0.011, 0.018, (-0.062, 0.050, 0.068), zh.M_BRASS),
        zh.box("GP_Arm", (0.008, 0.080, 0.005), (-0.045, 0.020, 0.076),
               zh.M_BRASS, rot=(0, 0, 0.22)),
        # 喇叭花 (小端接机座, 大端朝前上方)
        zh.cone("GP_Horn", 0.014, 0.130, (0.050, 0.0242, 0.1089), zh.M_BRASS,
                verts=18, rot=(axis_tilt, 0, 0), r_top=0.105),
        zh.cyl("GP_HornHole", 0.098, 0.004, (0.050, -0.0153, 0.1642), zh.M_INK,
               verts=18, rot=(axis_tilt, 0, 0)),
    ]
    return zh.join(parts, "gramophone")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    zh.__dict__["_FONT"] = None
    os.makedirs(OUT, exist_ok=True)
    builders = [
        ("abacus", build_abacus),
        ("kerosene_lamp", build_kerosene_lamp),
        ("enamel_spittoon", build_enamel_spittoon),
        ("gramophone", build_gramophone),
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
        print("ZHRELIC3 ->", path, "verts=", len(obj.data.vertices))
    print("ZHRELIC3_DONE")


main()
