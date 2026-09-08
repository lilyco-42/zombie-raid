"""中式资产尺寸体检: 逐个量 bbox (宽/深/高), 对照城市尺度找失衡件。

基准: 城市建筑 6-10m, 玩家身高 1.8m, 长城墙段 8×3.2×6.5(含垛口)。
判定: 高 > 12m 或 最大水平边 > 10m → 城内点缀会失衡(过大); 高 < 0.4m → 过小。
运行: blender --background --python tools/blender/measure_chinese.py
"""
import bpy, os, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import ROOT

ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
TALL_LIMIT = 12.0
WIDE_LIMIT = 10.0
SMALL_LIMIT = 0.4


def bbox_of_all():
    """场景内所有 MESH 对象的整体包围盒 (世界坐标)。"""
    mins = [1e9, 1e9, 1e9]
    maxs = [-1e9, -1e9, -1e9]
    found = False
    for ob in bpy.context.scene.objects:
        if ob.type != "MESH":
            continue
        found = True
        for co in ob.bound_box:
            w = ob.matrix_world @ __import__("mathutils").Vector(co)
            for i in range(3):
                mins[i] = min(mins[i], w[i])
                maxs[i] = max(maxs[i], w[i])
    if not found:
        return None
    return [maxs[i] - mins[i] for i in range(3)]


def main():
    files = sorted(glob.glob(os.path.join(ZH, "*.glb")))
    rows = []
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        try:
            bpy.ops.import_scene.gltf(filepath=f)
        except Exception as e:  # noqa: BLE001
            print("IMPORT_FAIL", name, e)
            continue
        size = bbox_of_all()
        if size is None:
            print("NO_MESH", name)
            continue
        rows.append((name, size[0], size[1], size[2]))

    print("=" * 78)
    print("%-24s %7s %7s %7s   %s" % ("asset", "W(X)", "D(Y)", "H(Z)", "flag"))
    print("-" * 78)
    for name, w, d, h in sorted(rows, key=lambda r: -r[3]):
        flags = []
        if h > TALL_LIMIT:
            flags.append("过高")
        if max(w, d) > WIDE_LIMIT:
            flags.append("过宽")
        if h < SMALL_LIMIT:
            flags.append("过小")
        print("%-24s %7.2f %7.2f %7.2f   %s" % (name, w, d, h, " ".join(flags)))
    print("-" * 78)
    print("total:", len(rows), "件")
    # 落盘报告, 便于回看
    out = os.path.join(ROOT, "assets", "_previews", "chinese_sizes.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("%-24s %7s %7s %7s\n" % ("asset", "W", "D", "H"))
        for name, w, d, h in sorted(rows, key=lambda r: -r[3]):
            fh.write("%-24s %7.2f %7.2f %7.2f\n" % (name, w, d, h))
    print("report ->", out)
    print("MEASURE_DONE")


main()
