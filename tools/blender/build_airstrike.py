"""空袭事件资产包: 轰炸机 / 炸弹 / 弹坑 / 防空警报塔。

复用 build_lc_assets 的材质与几何辅助; 产出:
- dynamic/event_bomber.glb (飞行事件体)
- dynamic/event_bomb.glb (下落事件体)
- static/event/crater.glb (地面痕迹)
- static/event/siren_tower.glb (警报塔)
"""
import bpy, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_lc_assets import (clear_scene, make_material, make_emissive,
                             box, join_objects, filtered_gltf_export,
                             STATIC_DIR, DYN_DIR)

EVENT_STATIC = os.path.join(STATIC_DIR, "event")
os.makedirs(EVENT_STATIC, exist_ok=True)

# 配色: 公司暗灰军械风
# 注意: clear_scene() 会清掉材质, 模块级引用会失效 (StructRNA removed),
# 因此材质放函数里, 每个 builder 开头 refresh。
def refresh_materials():
    g = globals()
    g["M_HULL"] = make_material("M_AS_Hull", (0.16, 0.17, 0.19), rough=0.55, metal=0.6)
    g["M_HULL2"] = make_material("M_AS_Hull2", (0.22, 0.23, 0.25), rough=0.6, metal=0.5)
    g["M_RED"] = make_material("M_AS_Red", (0.55, 0.08, 0.06), rough=0.6, metal=0.2)
    g["M_CANOPY"] = make_emissive("M_AS_Canopy", (0.10, 0.28, 0.30), strength=1.2)
    g["M_STROBE"] = make_emissive("M_AS_Strobe", (0.9, 0.1, 0.05), strength=6.0)
    g["M_OLIVE"] = make_material("M_AS_Olive", (0.18, 0.20, 0.12), rough=0.7, metal=0.3)
    g["M_WARN"] = make_material("M_AS_Warn", (0.75, 0.55, 0.05), rough=0.6, metal=0.1)
    g["M_CHAR"] = make_material("M_AS_Char", (0.045, 0.04, 0.038), rough=0.95)
    g["M_SMOKE"] = make_material("M_AS_Smoke", (0.30, 0.30, 0.32), rough=1.0)
    g["M_FIRE"] = make_emissive("M_AS_Fire", (1.0, 0.45, 0.08), strength=8.0)
    g["M_CONC"] = make_material("M_AS_Conc", (0.32, 0.32, 0.34), rough=0.9)
    g["M_PIT"] = make_material("M_AS_Pit", (0.02, 0.018, 0.016), rough=1.0)


def _cone(name, loc, r1, r2, depth, mat, verts=8, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=depth, location=loc,
                                    rotation=(math.radians(rot[0]),
                                              math.radians(rot[1]),
                                              math.radians(rot[2])))
    ob = bpy.context.object
    ob.name = name
    if mat:
        ob.data.materials.append(mat)
    return ob


def _cyl(name, loc, radius, depth, mat, rot=(0, 0, 0), verts=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius,
                                        depth=depth, location=loc,
                                        rotation=(math.radians(rot[0]),
                                                  math.radians(rot[1]),
                                                  math.radians(rot[2])))
    ob = bpy.context.object
    ob.name = name
    if mat:
        ob.data.materials.append(mat)
    return ob


def build_bomber():
    refresh_materials()
    """低多边形科幻轰炸机, 机头朝 -Y (与 Godot 前向一致), 全长 ~6m。"""
    parts = []
    parts.append(box("Bomb_Fuselage", (0, 0.2, 0), (1.1, 5.2, 0.9), M_HULL))
    # 机头四棱锥 (朝 -Y: 锥体默认朝 +Z, 转 -90° 绕 X)
    parts.append(_cone("Bomb_Nose", (0, -2.9, 0), 0.55, 0.02, 1.2, M_HULL2,
                       verts=4, rot=(-90, 0, 0)))
    # 座舱盖
    parts.append(box("Bomb_Canopy", (0, -1.7, 0.55), (0.7, 1.1, 0.35), M_CANOPY))
    # 后掠主翼 (沿 X 展开, 绕 Z 扫掠)
    for side in (1, -1):
        w = box(f"Bomb_Wing_{side}", (side * 2.0, 0.4, 0.12), (3.4, 1.5, 0.10), M_HULL2)
        w.rotation_euler.z = math.radians(-18 * side)
        parts.append(w)
        # 翼下发动机短舱
        e = _cyl(f"Bomb_Engine_{side}", (side * 2.5, -0.5, -0.32), 0.28, 1.3, M_HULL,
                 rot=(90, 0, 0))
        parts.append(e)
        parts.append(_cone(f"Bomb_EngineNoz_{side}", (side * 2.5, 0.35, -0.32),
                           0.28, 0.18, 0.4, M_CHAR, rot=(90, 0, 0)))
    # V 形尾翼
    for side in (1, -1):
        f = box(f"Bomb_Tailfin_{side}", (side * 0.55, 2.3, 0.75), (0.10, 1.2, 1.1), M_RED)
        f.rotation_euler.y = math.radians(35 * side)
        parts.append(f)
    # 机腹炸弹挂架
    parts.append(box("Bomb_Rack", (0, 0.2, -0.6), (0.6, 3.0, 0.12), M_HULL2))
    # 尾部红色频闪灯
    parts.append(_cyl("Bomb_Strobe", (0, 2.85, 0.25), 0.09, 0.12, M_STROBE))
    # 机身红色识别条
    parts.append(box("Bomb_Stripe", (0, 1.2, 0), (1.14, 0.35, 0.94), M_RED))
    return join_objects(parts, "Event_Bomber")


def build_bomb():
    refresh_materials()
    """低多边形航弹: 弹体竖直 (鼻锥朝 -Z), 高 ~1.2m。"""
    parts = []
    parts.append(_cyl("Bombshell_Body", (0, 0, 0.05), 0.16, 0.7, M_OLIVE, verts=10))
    parts.append(_cone("Bombshell_Nose", (0, 0, -0.5), 0.16, 0.01, 0.42, M_OLIVE,
                       verts=10))
    # 黄色警示环
    parts.append(_cyl("Bombshell_Band", (0, 0, -0.18), 0.165, 0.10, M_WARN, verts=10))
    # 尾锥 + 四片尾翼 (在 +Z 端)
    parts.append(_cone("Bombshell_Tail", (0, 0, 0.55), 0.16, 0.05, 0.3, M_OLIVE,
                       verts=10))
    for k in range(4):
        ang = k * 90
        fin = box(f"Bombshell_Fin_{k}",
                  (0.16 * math.cos(math.radians(ang)) * 0.6,
                   0.16 * math.sin(math.radians(ang)) * 0.6, 0.42),
                  (0.02, 0.22, 0.26), M_HULL2)
        fin.rotation_euler.z = math.radians(ang)
        parts.append(fin)
    return join_objects(parts, "Event_Bomb")


def build_crater():
    refresh_materials()
    """弹坑: 焦土圆盘 + 内凹坑 + 碎石 + 灼痕条, 直径 ~6m。"""
    parts = []
    # 地表焦土盘
    parts.append(_cyl("Crater_Ground", (0, 0, 0.03), 3.2, 0.06, M_CHAR, verts=24))
    # 内凹坑 (黑色, 略低于地表)
    parts.append(_cyl("Crater_Pit", (0, 0, -0.05), 1.5, 0.22, M_PIT, verts=18))
    # 环状碎石 (不规则 icosphere)
    for k in range(9):
        ang = k * 40 + (k * 17) % 23
        r = 1.7 + (k % 3) * 0.25
        s = 0.14 + (k % 4) * 0.05
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=s,
                                              location=(r * math.cos(math.radians(ang)),
                                                        r * math.sin(math.radians(ang)),
                                                        0.08 + s * 0.5))
        rock = bpy.context.object
        rock.name = f"Crater_Rock_{k}"
        rock.rotation_euler = (math.radians(k * 31), math.radians(k * 13), 0)
        rock.data.materials.append(M_CHAR)
        parts.append(rock)
    # 放射状灼痕 (薄扁条)
    for k in range(5):
        ang = k * 72 + 15
        s = box(f"Crater_Scorch_{k}",
                (2.6 * math.cos(math.radians(ang)), 2.6 * math.sin(math.radians(ang)), 0.035),
                (1.5, 0.5, 0.01), M_CHAR)
        s.rotation_euler.z = math.radians(ang + 90)
        parts.append(s)
    # 未爆哑弹 (斜插在坑边, 半埋)
    dud = _cyl("Crater_Dud", (1.1, -0.8, 0.15), 0.14, 0.9, M_OLIVE,
               rot=(65, 0, 20), verts=10)
    parts.append(dud)
    return join_objects(parts, "Event_Crater")


def build_siren():
    refresh_materials()
    """防空警报塔: 混凝土基座 + 4.5m 杆 + 四向号角 + 红色警示灯, 高 ~5.5m。"""
    parts = []
    parts.append(box("Siren_Base", (0, 0, 0.25), (1.0, 1.0, 0.5), M_CONC))
    parts.append(_cyl("Siren_Pole", (0, 0, 2.6), 0.09, 4.4, M_HULL2, verts=10))
    # 号角支架 (十字)
    parts.append(box("Siren_Bracket", (0, 0, 4.55), (1.5, 1.5, 0.08), M_HULL2))
    for k in range(4):
        ang = k * 90
        dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        horn = _cone(f"Siren_Horn_{k}",
                     (0.62 * dx, 0.62 * dy, 4.72), 0.14, 0.26, 0.55, M_RED,
                     verts=10, rot=(0, 0, 0))
        # 号角朝外下方: 绕轴倾斜 ~25°
        horn.rotation_euler = (math.radians(dy * 25), math.radians(-dx * 25),
                               math.radians(ang))
        horn.location = (0.55 * dx, 0.55 * dy, 4.70)
        parts.append(horn)
    # 顶部警示灯
    parts.append(_cyl("Siren_Beacon", (0, 0, 4.95), 0.12, 0.22, M_STROBE, verts=10))
    parts.append(box("Siren_Box", (0, 0.15, 4.2), (0.3, 0.4, 0.5), M_HULL))
    return join_objects(parts, "Event_SirenTower")


def _export(ob, path):
    filtered_gltf_export(
        path, export_format="GLB", export_yup=True, export_apply=False,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
    )
    print("AIRSTRIKE ->", path)


if __name__ == "__main__":
    for builder, path in (
        (build_bomber, os.path.join(DYN_DIR, "event_bomber.glb")),
        (build_bomb, os.path.join(DYN_DIR, "event_bomb.glb")),
        (build_crater, os.path.join(EVENT_STATIC, "crater.glb")),
        (build_siren, os.path.join(EVENT_STATIC, "siren_tower.glb")),
    ):
        clear_scene()
        ob = builder()
        _export(ob, path)
    print("AIRSTRIKE_DONE")
