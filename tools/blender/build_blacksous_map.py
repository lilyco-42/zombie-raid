"""BLACK SOULS 风格大地图: 失落帝国 × 渐进中式文化表达 (~134×84m)。

黑童话开放世界骨架 (借鉴 BLACK SOULS: 浓雾国度 / 童话原型 / 多重结局氛围),
中式元素按三阶段渐进融入 -- 换皮不换骨, 越深入"有人生活过的区域"痕迹越浓:

  Z1 黑森林   西 x[-58..-16]  死树阵 + 南瓜灯 + 白骨 + 引路灯(纯西式, 无中式)
  Z0 王城废墟 北 x[-8..28]y[16..37]  4m 模块城墙环 + 吊闸门 + 破墙 + 火把
              【中式·遗迹级】风化石狮守门 / 门墙褪色红灯笼 / 残壁红底标语
  Z4 疯茶会   中央 (2,0)  长桌 + 烛台 + 椅阵 + 沙发 + 地毯, 疯帽匠席位
              【中式·器物级】搪瓷缸上茶桌 (不死者收藏的东方器物)
  Z2 墓园     东南 x[14..46]y[-33..-13]  墓碑阵 + 石冢 + 棺 + 小石祠 (纯西式)
  Z3 庄园花园 东 x[45..71]y[7..33]  拱门绿篱迷宫 + 睡美人卧房 + 庄园废墟客厅
              【中式·生活级】石狮守拱门 / 红灯笼挂拱门与断墙
土路 pilgrim 路网连通五区; 威胁注记: 森林=明雷游荡, 城区=精英, 茶会=剧情触发。
产出 assets/maps/vendor/blacksous_map.glb
运行: blender --background --python tools/blender/build_blacksous_map.py
"""
import bpy, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_corridor import load_template, place, delete_templates, TEMPLATES
from build_vendor_lc import filtered_gltf_export, ROOT

MAPS = os.path.join(ROOT, "assets", "maps", "vendor")
DGN = os.path.join(ROOT, "assets", "static", "vendor", "dungeon")
HW = os.path.join(ROOT, "assets", "static", "vendor", "halloween")
FUR = os.path.join(ROOT, "assets", "static", "vendor", "furniture")
ZH = os.path.join(ROOT, "assets", "static", "vendor", "chinese")
OUT = os.path.join(ROOT, "assets", "maps", "vendor", "blacksous_map.glb")
MARK_OUT = os.path.join(ROOT, "assets", "maps", "vendor", "pickup_markers.glb")

LOADS = [
    # 王城废墟模块 (dungeon)
    ("wall", "wall", DGN), ("corner", "wall_corner", DGN),
    ("gated", "wall_gated", DGN), ("broken", "wall_broken", DGN),
    ("doorway", "wall_doorway", DGN), ("window", "wall_window_closed", DGN),
    ("arched", "wall_arched", DGN), ("pillar", "pillar", DGN),
    ("column", "column", DGN), ("rubble", "rubble_large", DGN),
    ("torch", "torch_lit", DGN), ("chest", "chest", DGN),
    ("barrel", "barrel_large", DGN), ("crates", "crates_stacked", DGN),
    ("trunk", "trunk_medium_A", DGN), ("chair", "chair", DGN),
    ("candle", "candle_triple", DGN),
    # 黑童话件 (halloween)
    ("grave", "gravestone", HW), ("marker", "gravemarker_A", HW),
    ("coffin", "coffin", HW), ("bone", "bone_A", HW),
    ("lantern", "lantern_standing", HW), ("pumpkin", "pumpkin_orange_jackolantern", HW),
    # 庄园家具 (furniture)
    ("table", "table_low", FUR), ("armchair", "armchair", FUR),
    ("couch", "couch", FUR), ("cabinet", "cabinet_medium", FUR),
    ("shelf", "shelf_B_large", FUR), ("rug", "rug_rectangle_A", FUR),
    ("lamp", "lamp_standing", FUR), ("bed", "bed_single_A", FUR),
    # 渐进中式件 (chinese)
    ("lion", "stone_lion", ZH), ("redlantern", "lantern_red", ZH),
    ("slogan", "slogan_tunnel", ZH), ("enamel", "enamel_set", ZH),
    # 中式 Phase 2 (圆明园遗址 × 生活器物)
    ("dashuifa", "dashuifa", ZH), ("ruincol", "ruin_columns", ZH),
    ("moongate", "moon_gate", ZH), ("screenwall", "screen_wall", ZH),
    ("stele", "stele", ZH), ("incense", "incense_burner", ZH),
    ("zhtable", "ba_xian_table", ZH), ("stool", "stool", ZH),
    ("vat", "water_vat", ZH),
    # 中式 Phase 3 (礼制/生活构件)
    ("paifang", "paifang", ZH), ("mendun", "mendun", ZH),
    ("bell", "bronze_bell", ZH), ("well", "well", ZH),
    ("otable", "offering_table", ZH), ("ash", "paper_ash", ZH),
    # 中式地标 (砖石体系, 避木构飞檐)
    ("greatwall", "greatwall_tower", ZH), ("pagoda", "brick_pagoda", ZH),
    ("bridge", "stone_bridge", ZH),
    # 中式地标 · 第二批 (土/石)
    ("tulou", "tulou", ZH), ("altar", "circular_altar", ZH),
    ("cliff", "grotto_cliff", ZH),
    # 中式地标 · 第三批 (砖石小品)
    ("beacon", "beacon_tower", ZH), ("citygate", "gate_platform", ZH),
    ("huabiao", "huabiao", ZH), ("rockery", "taihu_rock", ZH),
    # 中式地标 · 第四批 (长城体系, 模块化砖墙 + 石栏杆)
    ("gwsec", "greatwall_section", ZH), ("railing", "stone_railing", ZH),
    # 中式地标 · 第五批 (石作小品, 纯石/砖石)
    ("sutra", "stone_sutra", ZH), ("hpost", "hitching_post", ZH),
    ("spool", "stone_pool", ZH), ("slantern", "stone_lantern", ZH),
    # 中式地标 · 第六批 (生活级石作: 园扉/踏跺/磨盘/石槽)
    ("sarch", "stone_arch", ZH), ("stair", "stone_stair", ZH),
    ("smill", "stone_mill", ZH), ("strough", "stone_trough", ZH),
    # 中式地标 · 第七批 (园居石作: 石凳/石圆桌/石盆/碑林, 避木构飞檐)
    ("bench", "stone_bench", ZH), ("rtable", "stone_round_table", ZH),
    ("basin", "stone_basin", ZH), ("stelestl", "stone_stele_cluster", ZH),
    # 中式地标 · 第八批 (园居/礼制石作, 纯石)
    ("stone_pavilion", "stone_pavilion", ZH), ("wangzhu", "wangzhu", ZH),
    ("stone_bixi", "stone_bixi", ZH), ("stone_censer", "stone_censer", ZH),
    # 中式地标 · 第九批 (园居/礼制石作, 纯石)
    ("stone_hex_pavilion", "stone_hex_pavilion", ZH), ("sutra_cluster", "sutra_cluster", ZH),
    ("stone_water_beast", "stone_water_beast", ZH), ("lion_post", "lion_post", ZH),
    # 中式地标 · 第十批 (礼制/陵墓/守水石作, 纯石)
    ("stone_que", "stone_que", ZH), ("stone_screen", "stone_screen", ZH),
    ("stone_horse", "stone_horse", ZH), ("stone_toad", "stone_toad", ZH),
    # 中式地标 · 第十一批 (神道石像生补全/碑廊/石五供, 纯石)
    ("stone_sheep", "stone_sheep", ZH), ("stone_tiger", "stone_tiger", ZH),
    ("stele_gallery", "stele_gallery", ZH), ("stone_five_offering", "stone_five_offering", ZH),
    # 中式地标 · 第十二批 (桥栏/神道人像/石板平桥, 纯石)
    ("bridge_balustrade", "bridge_balustrade", ZH), ("stone_official", "stone_official", ZH),
    ("stone_general", "stone_general", ZH), ("stone_slab_bridge", "stone_slab_bridge", ZH),
]

TBL_H = 0.72  # table_low 估高, 烛台/器物落桌用, 渲染后校准


def _bake_pixels(img, sat, val):
    """像素级降饱和压暗 (glTF 导出不认 HSV 节点, 必须烘进像素)。"""
    import numpy as np
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    rgb = px[:, :3]
    lum = (rgb * np.array([0.299, 0.587, 0.114], dtype=np.float32)).sum(
        axis=1, keepdims=True)
    px[:, :3] = np.clip((lum + (rgb - lum) * sat) * val, 0.0, 1.0)
    img.pixels.foreach_set(px.reshape(-1))
    img.update()


def tone_down(keys, sat, val):
    """对模板件材质降饱和/压暗 (微调开源件原生卡通配色, 仅本图生效)。
    纹理走像素烘焙 (HSV 节点 glTF 不认); 纯色走 default_value。"""
    import colorsys
    for k in keys:
        tpl, *_ = TEMPLATES[k]
        stack, done = list(tpl.children), set()
        while stack:
            o = stack.pop()
            stack.extend(o.children)
            for slot in o.material_slots:
                m = slot.material
                if not m or m.name in done or not m.use_nodes:
                    continue
                done.add(m.name)
                bsdf = next((n for n in m.node_tree.nodes
                             if n.type == "BSDF_PRINCIPLED"), None)
                if not bsdf:
                    continue
                inp = bsdf.inputs["Base Color"]
                for link in list(inp.links):
                    img = getattr(link.from_node, "image", None)  # 图在节点上, 不在 socket 上
                    if img is not None and img.size[0]:
                        _bake_pixels(img, sat, val)
                        try:
                            img.pack()   # 确保 GLB 导出读取的是烘焙后像素
                        except RuntimeError:
                            pass
                if not inp.links:
                    r, g, b, a = inp.default_value
                    h, s, v = colorsys.rgb_to_hsv(r, g, b)
                    inp.default_value = (*colorsys.hsv_to_rgb(h, s * sat, v * val), a)


def refresh_materials():
    g = globals()
    g["M_DIRT"] = _mat("M_BS_Dirt", (0.10, 0.095, 0.088))      # 荒原暗土
    g["M_PATH"] = _mat("M_BS_Path", (0.135, 0.125, 0.108))     # 踩实的朝圣土路
    g["M_STONE"] = _mat("M_BS_Stone", (0.19, 0.19, 0.20))      # 王城石板
    g["M_GRAVE"] = _mat("M_BS_Grave", (0.085, 0.085, 0.092))   # 墓园黑土
    g["M_GARDEN"] = _mat("M_BS_Garden", (0.075, 0.11, 0.062))  # 秘园暗苔
    g["M_HEDGE"] = _mat("M_BS_Hedge", (0.055, 0.085, 0.045))   # 绿篱
    g["M_MARK"] = _emit("M_BS_Mark", (1.0, 0.45, 0.12), 3.0)   # 拾取标记暖光
    g["M_MARKBASE"] = _mat("M_BS_MarkBase", (0.16, 0.15, 0.14))
    g["M_DITCH"] = _mat("M_BS_Ditch", (0.05, 0.07, 0.08))      # 奈何沟 (暗水体)


def _mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs["Roughness"].default_value = 1.0
    return m


def _emit(name, rgb, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs["Emission Strength"].default_value = strength
    return m


def box(name, size, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0], size[1], size[2])
    o.data.materials.append(mat)
    return o


def join(parts, name):
    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    return o


def j(i):
    """确定性抖动, 免 random 模块。"""
    return ((i * 73) % 7 - 3) * 0.25


def build_ground():
    """地形: 荒原 + 路网 + 石板广场 + 墓园黑土 + 秘园苔地。顶面: 地 0.05 / 铺装 0.09。"""
    parts = [
        box("G_Dirt", (134, 84, 0.2), (8, 1, -0.05), M_DIRT),
        # 朝圣路网: 主路横贯 (黑森林→疯茶会→庄园), 支路三叉
        box("P_Main", (88, 5, 0.16), (2, 0, 0.01), M_PATH),
        box("P_Forest", (16, 4, 0.16), (-50, 0, 0.01), M_PATH),
        box("P_Castle", (5, 17, 0.16), (12, 8, 0.01), M_PATH),
        box("P_Grave", (4.5, 14, 0.16), (28, -7, 0.01), M_PATH),
        box("P_Garden", (4, 12, 0.16), (45.5, 5, 0.01), M_PATH),
        # 王城石板广场
        box("G_Castle", (38, 22, 0.16), (10, 26, 0.01), M_STONE),
        # 墓园 / 秘园
        box("G_Grave", (30, 20, 0.16), (28, -23, 0.01), M_GRAVE),
        box("G_Garden", (26, 26, 0.16), (58, 20, 0.01), M_GARDEN),
        # 绿篱迷宫环 (南口留 2.4m 豁口)
        box("H_N", (12, 0.8, 1.2), (58, 18.5, 0.69), M_HEDGE),
        box("H_W", (0.8, 9, 1.2), (52.2, 14, 0.69), M_HEDGE),
        box("H_E", (0.8, 9, 1.2), (63.8, 14, 0.69), M_HEDGE),
        box("H_SL", (5.6, 0.8, 1.2), (54.4, 9.5, 0.69), M_HEDGE),
        box("H_SR", (4.4, 0.8, 1.2), (61.8, 9.5, 0.69), M_HEDGE),
        # 奈何沟 (无主坟北, 暗水面凹陷; P_Grave 路跨其上, 桥接之)
        box("G_Ditch", (28.0, 3.2, 0.18), (28, -11.5, -0.04), M_DITCH),
    ]
    return join(parts, "ground_blacksous")


# 旧物拾取标记层: 与 assets/data/blacksous_story.json items 表一一对应。
# 标记 = 底座圆片 + 发光短柱 (几何简单功能件, 走 §3 例外条款, 非造型资产);
# enamel_cup 点已有搪瓷缸实物, 标记旁置 0.45m。
# 逐件独立对象不 join: 节点名 PickBase_<id>/PickBeam_<id>, 单独导出
# pickup_markers.glb 供 Godot 拾取后按名熄灭; 地图 GLB 不含标记。
PICKUPS = [
    ("enamel_cup", 1.55, 1.05, 0.09), ("family_letter", 25.8, -15.0, 0.09),
    ("ration_ticket", 0.0, 22.0, 0.09), ("work_badge", 15.8, 17.2, 0.09),
    ("jade_pendant", 9.4, 14.2, 0.09), ("couplet_paper", 56.5, 31.0, 0.09),
    ("tin_frog", -38.0, 2.2, 0.05), ("army_canteen", -8.0, 28.0, 0.09),
    ("cattail_fan", 59.2, 14.6, 0.09), ("abacus_bead", 3.6, -1.7, 0.09),
    ("family_photo", 25.0, -17.0, 0.09), ("red_string", 61.8, 9.5, 0.09),
]


def build_pickup_markers():
    parts = []
    for pid, px, py, pz in PICKUPS:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=0.04,
                                            location=(px, py, pz + 0.02))
        base = bpy.context.active_object
        base.name = f"PickBase_{pid}"
        base.data.materials.append(M_MARKBASE)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.10, depth=0.5,
                                            location=(px, py, pz + 0.29))
        beam = bpy.context.active_object
        beam.name = f"PickBeam_{pid}"
        beam.data.materials.append(M_MARK)
        parts += [base, beam]
    return parts


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    refresh_materials()
    for key, fname, d in LOADS:
        p = os.path.join(d, fname + ".glb")
        if not os.path.exists(p):
            raise FileNotFoundError(f"[{key}] {p}")
        load_template(fname, d, key=key)
    # 家具件原生配色是明亮卡通 (宝蓝沙发等), 与黑童话暗调冲突 → 降饱和压暗
    tone_down(["couch", "armchair", "bed", "cabinet", "shelf", "rug"], 0.25, 0.5)
    tone_down(["lamp"], 0.6, 0.85)

    build_ground()

    # ================= Z1 黑森林 (纯西式, 零中式) =================
    n = 0
    for tx in range(-54, -17, 6):          # 北林 x[-54..-18]
        for ty in (8, 13, 18, 23):
            n += 1
            if n % 8 == 0:
                continue                    # 留出林间空地
            place("trunk", tx + j(n), ty + j(n + 5), 0.05,
                  rot_z=(n * 53) % 360, scale=0.9 + ((n * 29) % 55) / 100)
    for ty in (-28, -23, -18, -13):         # 南林
        for tx in range(-54, -17, 6):
            n += 1
            if n % 7 == 0:
                continue
            place("trunk", tx + j(n), ty + j(n + 5), 0.05,
                  rot_z=(n * 53) % 360, scale=0.9 + ((n * 29) % 55) / 100)
    # 南瓜灯集群 (魔物留痕) + 白骨 + 引路灯
    place("pumpkin", -38, 2.2, 0.05)
    place("pumpkin", -36.6, 1.3, 0.05, rot_z=40)
    place("pumpkin", -39.2, 1.1, 0.05, rot_z=-25)
    place("bone", -30, -3, 0.05)
    place("bone", -44, 3.2, 0.05, rot_z=70)
    place("lantern", -48, 1.8, 0.05)
    place("lantern", -33.5, -1.6, 0.05)
    place("coffin", -46, -18, 0.05, rot_z=65)   # 半沉朽棺
    place("cliff", -46, 2, 0.05, rot_z=-20)     # 【地标】石窟崖壁 (西缘, 黑棘林中的天然石崖)

    # ================= Z0 王城废墟 (中式·遗迹级) =================
    # 南墙 y=16: 门洞居中 x=12
    for gx in (-4, 0, 4, 8):
        place("wall", gx, 16, 0.09)
    place("gated", 12, 16, 0.09)
    for gx in (16, 20, 24):
        place("wall", gx, 16, 0.09)
    # 北墙 y=36: 破损参差
    place("wall", -4, 36, 0.09)
    place("broken", 0, 36, 0.09)
    place("wall", 4, 36, 0.09)
    place("window", 8, 36, 0.09)
    place("wall", 12, 36, 0.09)
    place("broken", 16, 36, 0.09)
    place("wall", 20, 36, 0.09)
    place("wall", 24, 36, 0.09)
    # 西墙 x=-8 / 东墙 x=28
    place("wall", -8, 20, 0.09, rot_z=90)
    place("wall", -8, 24, 0.09, rot_z=90)
    place("broken", -8, 28, 0.09, rot_z=90)
    place("wall", -8, 32, 0.09, rot_z=90)
    place("wall", 28, 20, 0.09, rot_z=90)
    place("doorway", 28, 24, 0.09, rot_z=90)
    place("wall", 28, 28, 0.09, rot_z=90)
    place("window", 28, 32, 0.09, rot_z=90)
    # 四角
    place("corner", -8, 16, 0.09)
    place("corner", 28, 16, 0.09, rot_z=90)
    place("corner", 28, 36, 0.09, rot_z=180)
    place("corner", -8, 36, 0.09, rot_z=270)
    # 城内: 大水法残迹 (院心主景) + 残柱阵 + 残柱列 + 瓦砾 + 战利品
    for cx in (0, 6, 14, 20):
        place("column", cx, 33, 0.09)
    place("altar", -3, 27, 0.09)                  # 【地标】天坛式圜丘 (观水法台仪式点)
    place("dashuifa", 10, 26, 0.09)              # 【中式】圆明园大水法残迹
    for i, (rx, ry) in enumerate([(14.5, 29.2), (16.6, 31.2), (19.0, 29.8), (21.2, 31.6)]):
        place("ruincol", rx, ry, 0.09, rot_z=(i * 53) % 360)
    place("pagoda", 3, 33, 0.09)                 # 【地标】密檐砖塔 (院心北端, 永昌城内)
    place("rubble", 0, 22, 0.09, rot_z=15)
    place("rubble", 20, 32, 0.09, rot_z=-20)
    place("rubble", -4.5, 33, 0.09, rot_z=40)
    place("pumpkin", 1.8, 21.4, 0.09, rot_z=80)   # 魔物侵城痕迹
    place("bone", -1.5, 21, 0.09)
    place("chest", 16, 18.5, 0.09, rot_z=-90)
    place("barrel", 25, 34, 0.09)
    place("barrel", 23.8, 33.2, 0.09)
    place("crates", -5.5, 19, 0.09, rot_z=12)
    place("torch", 9.5, 17.5, 0.09)               # 门内火把
    place("torch", 14.5, 17.5, 0.09)
    place("mendun", 10.7, 16.8, 0.09)             # 【中式】门墩一对 (门洞内侧)
    place("mendun", 13.3, 16.8, 0.09)
    place("bell", 16.5, 19.5, 0.09)               # 【中式】铜钟 (撞钟三下=隐藏事件锚)
    place("well", 24.5, 19.8, 0.09)               # 【中式】井台辘轳
    place("citygate", 34, 24, 0.09, rot_z=90)      # 【地标】城台券门 (东门外瓮城, rot 90 券洞沿 X 朝东)
    # 【中式·遗迹级】石狮守门 (朝南迎宾客) + 门墙红灯笼 + 残壁标语
    place("lion", 9.4, 14.2, 0.09, rot_z=0, scale=1.2)
    place("lion", 14.6, 14.2, 0.09, rot_z=0, scale=1.2)
    place("redlantern", 10.7, 15.35, 2.5)
    place("redlantern", 13.3, 15.35, 2.5)
    place("slogan", 12, 34, 0.09)                 # 字面朝南, 穿门可见 (让位大水法北移贴墙)

    # 朝圣路牌坊 (迎宾, 联面朝南) + 路灯 (西式立灯, 引向王城)
    place("greatwall", -16, 26, 0.05, rot_z=90)   # 【地标】西墙外长城敌台 (墙段沿 Y 平行城墙)
    place("beacon", -16, 12, 0.05)               # 【地标】烽火台 (与敌台同列西线, 双重工事)
    place("lantern", 9.8, 10, 0.05)
    place("lantern", 14.2, 10, 0.05)
    place("paifang", 12, 6, 0.05)                 # 【中式】雾锁千秋骨/灯照野魂归
    place("huabiao", 8.6, 6, 0.05)                # 【中式】华表 (牌坊西侧礼仪柱)
    place("huabiao", 15.4, 6, 0.05)               # 【中式】华表 (牌坊东侧礼仪柱)

    # ================= 长城体系 (砖石, 模块化可拼接; 不冲渐进) =================
    # 西线 rampart: 敌台(-16,26)+烽火台(-16,12) 串成连续防线; 墙段 8m 一段,
    # rot_z=90 → 本地 X(长)朝世界 Y。段间由敌台/烽火台自然分隔, 只新增不删改。
    for wy in (-12, -4, 18, 34):
        place("gwsec", -16, wy, 0.05, rot_z=90)
    # 北端河套转折: 由 (-16,34) 向东, 含 1 处 -15° 弯折, 制造城墙拐角 (避免呆板直线)
    place("gwsec", -7, 34, 0.05, rot_z=0)
    place("gwsec", 1, 33.2, 0.05, rot_z=-15)
    place("gwsec", 9, 32.4, 0.05, rot_z=0)
    # 石栏杆点缀 (4m 段): 井台西缘短栏 + 月洞门外侧园缘
    place("railing", 22.5, 19.8, 0.05, rot_z=90)
    place("railing", 46.5, 12, 0.05, rot_z=0)
    place("railing", 49.5, 12, 0.05, rot_z=0)

    # ================= 中式地标 · 第五批 (石作小品, 纯石) =================
    # 只新增不删改。落位: 经幢立仪式角, 拴马桩夹东门, 水池+石灯入园。
    place("sutra", 10, 31, 0.05)                     # 【石作】石经幢 (永昌城内仪式角, 近圜丘/塔)
    place("hpost", 30, 27, 0.05, rot_z=20)           # 【石作】拴马桩 (东门券门外, 夹道)
    place("hpost", 38, 21, 0.05, rot_z=-15)
    place("spool", 54, 20, 0.05)                     # 【石作】太液池 (无人同坐园, 水景)
    place("slantern", 50.5, 16, 0.05)                # 【石作】石灯笼 (池畔, 平顶非飞檐)

    # ================= 中式地标 · 第六批 (生活级石作) =================
    # 只新增不删改。园扉/踏跺/磨盘/石槽 均落无人同坐园 (生活级渐进最深处)。
    place("sarch", 48, 5, 0.05, rot_z=0)             # 【石作】石坊 (无顶石牌坊, 园南扉)
    place("stair", 54, 26, 0.05, rot_z=0)            # 【石作】石阶 (园中踏跺, 近太液池)
    place("smill", 46, 22, 0.05)                     # 【石作】石磨 (生活级农作器物)
    place("strough", 58, 22, 0.05)                   # 【石作】石槽 (园中汲水/饮畜)

    # ================= 中式地标 · 第七批 (园居石作) =================
    # 只新增不删改。石凳/石圆桌成对落园中, 石盆近西缘, 碑林立园东扉。
    place("bench", 49, 11, 0.05)                     # 【石作】石凳 (园中休憩座)
    place("rtable", 52, 11, 0.05)                    # 【石作】石圆桌 (与石凳成对, 平顶非飞檐)
    place("basin", 44, 17, 0.05)                     # 【石作】石盆 (叠石花盆, 园西缘)
    place("stelestl", 60, 15, 0.05, rot_z=10)        # 【石作】碑林 (三碑错落, 园东扉礼仪点)

    # ================= 中式地标 · 第八批 (园居/礼制石作) =================
    # 只新增不删改。石亭落园心近池, 望柱成对列园门, 赑屃配碑林, 石鼎立园心香火。
    place("stone_pavilion", 54, 14, 0.05)              # 【石作】无顶石亭 (平顶石板, 避飞檐, 近太液池)
    place("wangzhu", 47, 8, 0.05)                      # 【石作】望柱 (云纹石柱, 园门列柱)
    place("wangzhu", 51, 8, 0.05)                      # 【石作】望柱 (成对)
    place("stone_bixi", 60, 11, 0.05)                 # 【石作】石赑屃碑座 (配碑林)
    place("stone_censer", 50, 22, 0.05)               # 【石作】石鼎香炉 (园心香火)

    # ================= 中式地标 · 第九批 (园居/礼制石作) =================
    # 只新增不删改。六角亭立园东北, 经幢群居园西, 镇水兽守太液池, 望柱石狮成对列园门。
    place("stone_hex_pavilion", 60, 30, 0.05)           # 【石作】六角石亭 (平顶六边, 园东北)
    place("sutra_cluster", 40, 24, 0.05)               # 【石作】石经幢群 (三幢错落, 园西)
    place("stone_water_beast", 58, 16, 0.05)           # 【石作】镇水兽·石犀 (守太液池东)
    place("lion_post", 42, 6, 0.05)                   # 【石作】望柱石狮 (成对守园门)
    place("lion_post", 46, 6, 0.05)                   # 【石作】望柱石狮 (成对)

    # ================= 中式地标 · 第十批 (礼制/陵墓/守水石作) =================
    # 只新增不删改。石阙成对列园东门, 石屏风立仪卫位, 石马成对列义冢神道, 石蟾守太液池西。
    place("stone_que", 36, 12, 0.05)                 # 【石作】石阙 (汉阙式, 成对列园东门)
    place("stone_que", 40, 12, 0.05)                 # 【石作】石阙 (成对)
    place("stone_screen", 36, 20, 0.05)              # 【石作】石屏风 (观水法式三屏, 仪卫位)
    place("stone_horse", 22, -20, 0.05)              # 【石作】石像生·石马 (义冢神道仪卫)
    place("stone_horse", 28, -20, 0.05)              # 【石作】石像生·石马 (成对)
    place("stone_toad", 48, 24, 0.05)                # 【石作】镇水兽·石蟾 (守太液池西)

    # ================= 中式地标 · 第十一批 (神道/碑廊/祭器) =================
    # 只新增不删改。石羊石虎接续石马列义冢神道, 碑廊立神道东, 石五供落园北祭台。
    place("stone_sheep", 22, -24, 0.05)             # 【石作】石像生·石羊 (神道仪卫, 成对)
    place("stone_sheep", 28, -24, 0.05)             # 【石作】石像生·石羊 (成对)
    place("stone_tiger", 22, -28, 0.05)             # 【石作】石像生·石虎 (神道仪卫, 成对)
    place("stone_tiger", 28, -28, 0.05)             # 【石作】石像生·石虎 (成对)
    place("stele_gallery", 34, -20, 0.05)           # 【石作】碑廊 (四碑连墙, 平顶廊板)
    place("stone_five_offering", 50, 26, 0.05)      # 【石作】石五供 (香炉+双烛台+双花瓶)

    # ================= 中式地标 · 第十二批 (桥栏/神道人像/平桥) =================
    # 只新增不删改。文臣武将接续石虎列神道最南, 相向而立; 石板平桥跨太液池, 桥栏组列园东。
    place("stone_official", 22, -32, 0.05, rot_z=90)    # 【石作】石像生·文臣 (神道, 面朝路)
    place("stone_official", 28, -32, 0.05, rot_z=-90)   # 【石作】石像生·文臣 (相向成对)
    place("stone_general", 22, -36, 0.05, rot_z=90)     # 【石作】石像生·武将 (神道最南)
    place("stone_general", 28, -36, 0.05, rot_z=-90)    # 【石作】石像生·武将 (相向成对)
    place("stone_slab_bridge", 54, 20, 0.05)            # 【石作】石板平桥 (跨太液池)
    place("bridge_balustrade", 60, 26, 0.05)            # 【石作】石桥栏板组 (抱鼓石收头, 园东)

    # ================= Z4 疯茶会 (中式·器物级) =================
    place("rug", 2, 0, 0.095)
    place("zhtable", 2, 0, 0.09)                   # 【中式】八仙桌主桌 (桌高 0.85)
    place("candle", 1.4, 0.5, 0.94, rot_z=30)
    place("candle", 2.6, -0.4, 0.94, rot_z=-50)
    place("enamel", 2, 0.7, 0.94)                  # 【中式】搪瓷缸上桌
    place("stool", 0.2, 1.7, 0.09, rot_z=45)
    place("chair", 3.8, 1.6, 0.09, rot_z=-45)
    place("chair", 0.4, -1.7, 0.09, rot_z=135)
    place("stool", 3.2, -2.3, 0.09, rot_z=-135)    # 让位拾取标记 (3.6,-1.7)
    place("chair", 5.5, -2.6, 0.09, rot_z=80)      # 被掀翻推开的椅子
    place("couch", 2, 3.4, 0.09, rot_z=180)        # 疯帽匠席
    place("lamp", 4.8, 1.9, 0.09, rot_z=-30)
    place("pumpkin", 0.1, 3.3, 0.09)
    place("bone", -1.8, -1.3, 0.09)
    place("bone", 5.1, 0.7, 0.09, rot_z=45)

    # ================= Z2 墓园 (纯西式) =================
    m = 0
    for gx in (18, 24, 30, 36, 42):
        for gy in (-30, -26, -22):
            m += 1
            if m % 5 == 0:
                continue
            key = "grave" if m % 3 else "marker"
            place(key, gx + j(m), gy + j(m + 3), 0.09,
                  rot_z=((m * 37) % 4 - 1.5) * 8)
    place("marker", 20, -18, 0.09, rot_z=10)
    place("marker", 34, -28.5, 0.09, rot_z=-15)
    place("coffin", 16, -31.5, 0.09, rot_z=25)
    # 小石祠: 三面墙 + 棺 + 立灯 + 石碑一对 + 香炉 (【中式】义冢祭祀)
    place("wall", 25, -17, 0.09)
    place("wall", 23, -15, 0.09, rot_z=90)
    place("wall", 27, -15, 0.09, rot_z=90)
    place("coffin", 25, -15.6, 0.09)
    place("lantern", 23.4, -13.4, 0.09)
    place("lantern", 26.6, -13.4, 0.09)
    place("stele", 22, -16.2, 0.09)
    place("stele", 28, -16.2, 0.09)
    place("incense", 25, -13.6, 0.09)
    place("otable", 25, -12.4, 0.09, rot_z=180)   # 【中式】供桌 (面朝祭拜来向)
    place("ash", 23.2, -12.7, 0.09)               # 【中式】纸钱灰堆
    place("bridge", 28, -11.5, 0.05, rot_z=90)    # 【地标】奈何桥 (跨暗水沟, rot 90 桥长沿 Y)
    place("tulou", 58, -30, 0.05)                # 【地标】福建土楼残迹 (东南遗世聚落)
    place("bone", 32, -24, 0.09)
    place("bone", 22, -28, 0.09, rot_z=90)
    place("pumpkin", 44, -14, 0.09, rot_z=15)

    # 东部死木带 (填补空旷)
    for i, (tx, ty) in enumerate([(52, -36), (58, -38), (64, -36), (60, -15),
                                  (-44, -28), (-52, -33)]):
        place("trunk", tx, ty, 0.05, rot_z=(i * 97) % 360,
              scale=0.95 + (i % 3) * 0.15)
    place("bone", 50, -24, 0.05, rot_z=30)
    place("pumpkin", 55, -18, 0.05, rot_z=-40)
    place("bone", -48, -29.5, 0.05, rot_z=140)

    # ================= Z3 庄园与秘密花园 (中式·生活级) =================
    # 月洞门入口 (朝西) + 石狮 + 红灯笼
    place("moongate", 45, 12, 0.09, rot_z=90)
    place("rockery", 48.5, 12, 0.09)             # 【中式】太湖石 (入门障景, 中式园林灵魂)
    place("lion", 45, 9.2, 0.09, rot_z=-90)
    place("lion", 45, 14.8, 0.09, rot_z=-90)
    place("redlantern", 44.4, 12, 2.5)
    # 绿篱迷宫内: 睡美人卧房 (白雪公主玻璃棺原型 → 摩登改写)
    place("rug", 58, 14, 0.095)
    place("bed", 58, 15.6, 0.09, rot_z=180)
    place("lamp", 56, 12.4, 0.09, rot_z=30)
    place("screenwall", 58, 20.6, 0.09, rot_z=180)  # 【中式】影壁 (卧房与庄园之间)
    # 庄园废墟客厅 (无顶, 断柱尚立)
    place("column", 52, 30, 0.09)
    place("column", 64, 30, 0.09)
    place("broken", 58, 32.5, 0.09)
    place("couch", 56, 27, 0.09, rot_z=90)
    place("armchair", 60.5, 26.5, 0.09, rot_z=-120)
    place("table", 58, 25.5, 0.09)
    place("candle", 58, 25.5, 0.09 + TBL_H)
    place("cabinet", 65, 29, 0.09, rot_z=-90)
    place("shelf", 50.5, 29, 0.09, rot_z=90)
    place("chest", 52, 24.5, 0.09, rot_z=20)
    place("barrel", 66, 25, 0.09)
    place("vat", 50.6, 26.2, 0.09)                  # 【中式】太平缸
    place("incense", 66.5, 31.8, 0.09, rot_z=90)    # 【中式】园角香炉
    place("redlantern", 56.5, 31.85, 2.4)          # 【中式】断墙挂灯
    place("bone", 62, 22.5, 0.09, rot_z=60)        # 花园亦有兽迹

    delete_templates()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    # 标记单独导出 (仅选中对象, 按名熄灭), 再从场景移除, 地图 GLB 保持纯净
    mark_parts = build_pickup_markers()
    bpy.ops.object.select_all(action="DESELECT")
    for o in mark_parts:
        o.select_set(True)
    filtered_gltf_export(
        MARK_OUT, export_format="GLB", export_yup=True, export_apply=False,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
        use_selection=True,
    )
    for o in mark_parts:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    filtered_gltf_export(
        OUT, export_format="GLB", export_yup=True, export_apply=False,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
    )
    print("BLACKSOUS_MARKERS ->", MARK_OUT)
    print("BLACKSOUS_MAP ->", OUT)


main()
