---
name: lyco
description: 开源 3D 素材收编与组装管线（CC0/CC-BY 素材 → Blender 归一化 → 微调/压缩/旋转/重叠/组合 → 整图 GLB → 渲染目检 → Godot 接入）。当用户提到 /lyco、开源素材、收编、组装地图、拼场景、或要求“不要自己生成、用开源件组合”时使用。
---

# LYCO —— 开源素材收编与组装管线

核心立场：**借开源件做微调/压缩/旋转/重叠/组合，不凭空代码生成新形状**（几何极简单的功能件除外，见 §1 例外条款）。
本管线在 fps-chaf 项目（Godot 4 + Blender 5.x headless）历 15–37 轮打磨（中式渐进 36 轮 + LC 四类循环），以下坑位均为实测。

工程默认路径：`C:\Users\liuqi\dev\fps-chaf`（Blender 与 Godot 命令都从这里起）。

---

## 1. 铁律与例外条款

**铁律**
- 只新增不删改：新资产/新脚本放新文件，不破坏既有产物。
- 缺件优先查素材库（`assets/static/vendor/` 下 dungeon / furniture / halloween / space_dark / chinese…），缺了用现有件**组合拼**（如：石祠 = 三面墙 + 棺 + 立灯），最后才考虑收编或新建。
- 授权：只收 CC0 / CC-BY；CC-BY 必须登记署名。Sketchfab 下载需 token，poly.pizza 需环境变量 `POLY_PIZZA_KEY`（CDN 直下免鉴权）。

**例外条款（允许程序化生成）**
- 平整地形盒、拾取光柱/底座等功能件；
- 参数化小器物（灯笼、石狮、香炉、月洞门、牌坊、水缸…）——**冲天柱式牌坊这类无顶做法是绕开飞檐的自建正解**；
- **绝不自建**：飞檐屋顶、斗拱、瓦作、脊兽、隔扇门窗、漏窗、藻井、亭廊塔桥、太湖石（一律走收编）。

---

## 2. OORDA 决策循环（每轮先跑这一圈，再动手）

不是上来就建模。每轮先走 **O→O→R→D→A** 一圈，两道硬门槛：**O 的理解门槛**（没看懂用户的话就先搜+先问）与 **R 的 ROI 门槛**（不过门槛不动工）。

- **O · Observe 观察（理解门槛 + 查库/盘点）**：
  - **理解门槛（先于一切）**：若用户的话/提示词**没看懂、有歧义或含陌生概念** → 强制两步，缺一不可：
    1. **强制同步信息**：WebFetch/WebSearch **至少搜一次**，同步外部术语/上下文/同类项目，目的是弄清**用户真实核心需求**是什么；
    2. **强制提问**：直接问用户"你的核心需求是什么"，不猜、不脑补、不将就着做。
    > 没同步信息 + 没问清就动手 = 违规；理解检查通过才准进 Orient/R。
  - 查库/盘点：已完成什么、缺什么。列出缺口（四类=道具/人物/场景/怪物，或分区/分区件），引用上轮 memory 的资产盘点，**避免重复劳动**。
- **O · Orient 研判（对齐基线）**：风格基线（低模/破旧工业/压抑废土；中式皮肉=离生活越近越中式）、命名与目录约定（`assets/dynamic/` 动态件、`assets/static/vendor/<kit>/` 静态件）、与既有件是否冲突/重复。
- **R · ROI 评估（投入产出比门槛）**：值不值得做、做多偷懒。
  - **产出值** = 玩法价值（是否服务主循环/用途明确）+ 辨识度 + 是否补缺 + 风格契合 + 可复用度（能摆几处/几张图）。
  - **投入本** = 工时 + 是否需收编（授权/下载/归一化）+ 验证成本。
  - **红线**：碰自建禁区（飞檐/斗拱/瓦作/脊兽/隔扇/漏窗/藻井/亭廊塔桥/太湖石）→ 一律收编，成本再高也不自建。
  - **偷懒档位**：能复用就别拼装，能拼装就别程序化，能程序化就别收编，能收编就别自建——选成本最低且过基线的做法；产出值撑不起成本就跳过或换件。
  - **范围上限**：每轮**只交一件**小成果（范围=成本上限）。
- **D · Decide 决策（定件+定档）**：选定本轮一件 + 做法档位 + 落位/玩法用途，写进记录。
- **A · Act 行动（执行+验证+记录）**：走 §3 六步工作流 → 过 §5 验证清单 → 记资产名/路径/进度状态。

> 中式 LC 语境 ROI 示例：废料件选**中式旧物**（暖水瓶/铁皮罐头/搪瓷缸——高玩法价值 + 基础几何低成本 + 贴合中式皮肉），不选通用西方螺栓（风格契合低、与中式皮肉不符）。

---

## 3. 六步工作流（= OORDA 的 A 阶段执行细节）

1. **查库** → 现有 kit 里找可代用件，列 LOADS 表（`("key", "file", DIR)`）。
2. **收编**（如需）：下载 → 核授权 → Blender 归一化（尺寸/朝向/原点底面中心）→ 放入 `assets/static/vendor/<kit>/`。
3. **组装**：写 `build_*.py`，用模板引擎
   ```python
   from build_corridor import load_template, place, delete_templates, TEMPLATES
   load_template(fname, d, key=key)     # 底面中心对齐
   place(key, x, y, z, rot_z=0, scale=1.0)
   delete_templates()                    # 导出前清模板
   ```
   4m 网格约定：KayKit dungeon 墙 4×1×4 沿 X，侧墙 `rot_z=90`，四角 `wall_corner` 0/90/180/270。
4. **微调**：`tone_down(keys, sat, val)` 像素烘焙降饱和压暗开源件卡通配色（见 §3 坑 3）。
5. **导出**：`filtered_gltf_export(OUT, export_format="GLB", export_yup=True, export_apply=False, export_materials="EXPORT", export_cameras=False, export_lights=False)`；需拆件导出加 `use_selection=True`。
6. **验证**：渲染 3–4 机位目检 → Godot 场景探针（`<TAG>_PASS`）→ CC-BY 归档。

---

## 4. 已知坑清单（必读，逐条踩过）

| # | 坑 | 修法 |
|---|---|---|
| 1 | Bash 工作目录**不跨命令保持** | 每条命令显式 `cd /c/Users/liuqi/dev/fps-chaf && …` |
| 2 | `filtered_gltf_export` 默认导出**整个场景**（拆件 GLB 会变大） | 先 `select_all(DESELECT)` + 选中目标，再 `use_selection=True` |
| 3 | **glTF 导出不认 Hue/Saturation 节点**，纹理调色失效 | 改像素烘焙（`pixels.foreach_get/set`）后 `img.pack()` |
| 4 | 材质图在 `link.from_node.image`，**不在 `from_socket`**（getattr 静默 None） | 用 `link.from_node` |
| 5 | `import build_chinese` 会执行其模块底 `main()`，之后 `read_factory_settings` 使缓存字体失效 → `ReferenceError: VectorFont has been removed` | 重置后 `zh.__dict__["_FONT"] = None` 懒重载 |
| 6 | `orphans_purge` 清掉未被引用的新建材质（StructRNA removed） | 批量构建只删对象不 purge；每个 builder 前 `refresh_materials()` |
| 7 | CJK 字模朝向：再加 `rot_z=π` 会**镜像** | `simhei.ttf` → text extrude → convert MESH；`rot=(π/2,0,0)` 字面朝 -Y |
| 8 | 浅色 albedo 在 AgX 下**过曝**（锈橙偏粉褐） | light_mult 分档：大件排 0.32–0.35、街景 0.42–0.5 |
| 9 | `-s` SceneTree 脚本里 `await physics_frame` **永不触发**，进程挂死 | 帧循环验证改场景化（Node + tscn）+ `create_timer` + 20s 看门狗；跑 Godot 一律套 `timeout 90` |
| 10 | GDScript 无类型变量成员访问返回 Variant → 类型推断解析报错 | 显式标类型；`get_world_3d()` 只在 **Node3D** 上有 |
| 11 | 管道 `\| head` 会 SIGTERM | 长命令 `run_in_background` + 日志落盘 + grep |
| 12 | Godot 4.7 API：`set_item_shape`/`set_cell` 不存在 | `set_item_shapes(id,[shape,Transform3D()])`、`set_cell_item` |
| 13 | 拾取标记烘进整图 GLB 后无法单灭 | 标记单独导出（`use_selection`），节点名 `PickBase_<id>`/`PickBeam_<id>`，Godot 侧 `find_child` 按名隐藏 |
| 14 | **Edit 工具偶发「成功不落盘」**：同文件多处编辑部分静默丢失（Round31 LOADS 表、lyco-skill SKILL.md 两次复现；报 success 但原文未变，差点把半成品推上 GitHub） | 多处/关键编辑一律 **python 确定性替换（带 count==1 断言）+ 事后 grep 校验**，校验通过再 commit/push；远端校验拉原文（gh api contents），别信 code search 索引 |

**坐标换算定案**：Blender `(x, y)` → Godot `(x, -y)`（glTF Y-up）；探针用向下射线命中墙顶高度实证。
**MeshLibrary 锚点**：item bbox 底面中心对齐原点 → 地板顶面 = 格底 + 0.15m，零偏移可用。

---

## 5. 验证清单（收工前逐项）

- [ ] Blender 构建日志出现 `…_DONE` / `…-> <path>`，无 Traceback
- [ ] GLB 体积合理（地图 2–4MB；拾取标记 ~160KB；单件 <1MB）
- [ ] 渲染预览：俯瞰 + 至少 1 个街景（相机必须站几何内部，别被墙挡）
- [ ] 中式/调性检查：无高饱和卡通色溢出（烘焙生效）
- [ ] Godot：`godot --headless --path . --import` 后跑探针 → `<TAG>_PASS`
- [ ] CC-BY 署名登记（如本轮收编了新件）
- [ ] 记录资产名/文件路径/进度状态 + 本轮 ROI 档位入 memory（OORDA 的 D/A 交付）
