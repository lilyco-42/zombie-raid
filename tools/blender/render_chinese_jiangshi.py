"""中式僵尸挂件预览: 把四件挂件按骨骼坐标摆到 KayKit 骷髅(Minion, 无头饰)身上做真目检。

骨骼坐标从导入的 ARMATURE 里现读 (不硬编码), 正面方向由 toes.l/toes.r 的中点相对
hips 求出 —— 与 Godot 端 chinese_jiangshi.gd 的 up/fwd 推导同源, 预览即诚实。

产出 assets/_previews/:
  zh_jiangshi_full.png   全身正面
  zh_jiangshi_head.png   头部特写 (顶戴 + 额前黄符)
  zh_jiangshi_chest.png  上身特写 (方补 + 铜钱串)
"""
import bpy, os, sys, mathutils

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import (import_gltf, setup_scene, add_camera,
                                    add_ground, render_to, pick_action, ROOT)

ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
HOST = os.path.join(ROOT, "assets", "kaykit", "skeletons", "Skeleton_Minion.glb")

# (文件名, 骨名, 沿骨架上方向偏移, 沿正面方向偏移) —— 与 chinese_jiangshi.gd 的 SPECS 一致
SPECS = [
    # (文件名, 骨名, 沿骨架上方向偏移, 沿正面方向偏移) — 依据蒙皮网格实测, 见 build 脚本头注释
    ("jiangshi_hat", "head", 0.810, 0.000),
    ("jiangshi_talisman", "head", 0.600, 0.400),
    ("jiangshi_buzi", "chest", 0.030, 0.371),
    ("jiangshi_coins", "hips", 0.194, 0.240),
]


def bone_map(arm):
    return {b.name: b for b in arm.data.bones}


def place(arm):
    """读骨骼, 计算 up/fwd, 把四件挂件摆上去。返回 (up, fwd, 骨点字典)。"""
    bm = bone_map(arm)
    hips = bm["hips"].head_local.copy()
    head = bm["head"].head_local.copy()
    up = (head - hips)
    up.z = 0.0
    if up.length < 1e-6:
        up = mathutils.Vector((0.0, 0.0, 1.0))
    up = mathutils.Vector((0.0, 0.0, 1.0))     # 骨架空间的上就是 +Z (z-up)
    toes = [bm[k].head_local.copy() for k in ("toes.l", "toes.r") if k in bm]
    fwd = mathutils.Vector((0.0, -1.0, 0.0))
    if len(toes) == 2:
        t = (toes[0] + toes[1]) * 0.5 - hips
        t.z = 0.0
        if t.length > 1e-4:
            fwd = t.normalized()
    pts = {"head": head, "chest": bm["chest"].head_local.copy(), "hips": hips}
    for fname, bone, dup, dfw in SPECS:
        objs = import_gltf(os.path.join(ZH, fname + ".glb"))
        base = pts[bone] + up * dup + fwd * dfw
        # 只挪根节点 (父不在本批返回集里的对象); 父子都挪会位移翻倍 (首轮踩中:
        # 帽子被顶到 ~2.7m 高空, 相机全被帽檐挡住)
        for o in objs:
            if o.parent is None or o.parent not in objs:
                o.location += base
        bpy.context.view_layer.update()
        mn = mathutils.Vector((1e9,) * 3); mx = mathutils.Vector((-1e9,) * 3)
        for o in objs:
            if o.type != "MESH":
                continue
            for c in o.bound_box:
                w = o.matrix_world @ mathutils.Vector(c)
                mn = mathutils.Vector(map(min, mn, w)); mx = mathutils.Vector(map(max, mx, w))
        print("PLACE", fname, "min", tuple(round(v, 3) for v in mn),
              "max", tuple(round(v, 3) for v in mx), "visible=", all(o.visible_get() for o in objs))
    return up, fwd, pts


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    add_ground(size=8)
    setup_scene()
    bpy.context.scene.view_settings.view_transform = "Filmic"
    bg = bpy.data.worlds["World"].node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Strength"].default_value = 0.5
    for lt in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        lt.data.energy *= 0.55


def load_host():
    objs = import_gltf(HOST)
    arm = next((o for o in objs if o.type == "ARMATURE"), None)
    if arm is None:
        raise RuntimeError("no armature in " + HOST)
    act = pick_action(arm, prefer=("idle", "walk"))
    if act is not None:
        if not arm.animation_data:
            arm.animation_data_create()
        arm.animation_data.action = act
        bpy.context.scene.frame_set(1)
    return arm


# 0) 挂件单独四连拍 (无宿主, 排查材质/形状)
for fname, _b, _u, _f in SPECS:
    reset()
    import_gltf(os.path.join(ZH, fname + ".glb"))
    add_camera("Cam", (0.0, -0.75, 0.14), (0.0, 0.0, -0.04), 40.0)
    render_to("zh_jiangshi_acc_" + fname + ".png")

# 1) 全身正面 (远景广角)
reset()
arm = load_host()
up, fwd, pts = place(arm)
add_camera("Cam", (0.4, -6.2, 1.20), (0.0, 0.0, 1.02), 40.0)
render_to("zh_jiangshi_full.png")

# 2) 头部特写 (顶戴 + 额前黄符)
reset()
arm = load_host()
up, fwd, pts = place(arm)
hp = pts["head"]
add_camera("Cam", (0.05, -1.85, hp.z + 0.66), (0.0, 0.0, hp.z + 0.56), 50.0)
render_to("zh_jiangshi_head.png")

# 3) 上身特写 (方补 + 铜钱串)
reset()
arm = load_host()
up, fwd, pts = place(arm)
cp = pts["chest"]
add_camera("Cam", (0.05, -2.05, cp.z + 0.18), (0.0, 0.0, cp.z + 0.05), 50.0)
render_to("zh_jiangshi_chest.png")
print("ZHJIANGSHI_PV_DONE")
