# server/ 内容运营工作区 — 职责声明与任务看板

> 本文件是服务端 AI 与 UI AI 并行工作时的**单一事实来源**。改任何契约前先读这里。
> 自动化循环按「任务看板」逐项推进，每完成一项打勾并更新底部状态行。

## 职责区域（冲突分离边界）

### 服务端 AI（本文件作者）负责 — 其他协作者勿改

- `server/` 全部（Cargo workspace：`protocol` + `server-bin`）
- `server/content/*.toml` 内容表（物品/僵尸/规则/活动）
- 服务端测试：`tests/test_lcg.gd`、`tests/ws_roundtrip.gd`、`tests/test_ws_codec.gd`
- `docs/SERVER_DEV.md`

### UI AI / 关卡侧负责 — 服务端 AI 不碰

- `game/` 下全部 UI（主界面 / 背包 / 仓库 / 商店场景与脚本）
- `assets/` 美术与音频
- `game/scripts/world_raid.gd`、`outer_ward_*.gd` 等玩法场景脚本

### 共享接口（改动需在 git commit message 里显式标注 `[协议变更]` 或 `[内容表变更]`）

- **协议**：`protocol` crate 的 `C2S`/`S2C` 枚举 = 唯一线格式（bincode legacy，黄金字节测试钉死）。
  UI 侧只消费 `net.gd` 已有信号（`seed_received` / `zombie_snapshot` / …），不直接编解码。
- **net.gd 的 `_dispatch_s2c` / `rpc_*`**：协议消费侧归服务端 AI 维护编解码分支，UI 挂自己的业务逻辑。
- **内容 ID**：`items.id` / `zombies.id` 一经发布**永不复用、永不改含义**（10 年契约）。

## 任务看板（商业化优先排序）

- [x] **T1** 职责声明与看板（本文件）
- [x] **T2** 内容表骨架 `server/content/{zombies,items,raid}.toml` — 1:1 复刻现行为（数值 = world.rs 现有常量），items 表含商店字段（价格/可购/限时）作为商业化根基
- [x] **T3** `protocol::content` 加载器 + 校验器（schema 合法 / ID 唯一 / 数值范围 / 引用存在）+ 单元测试
- [x] **T4** World 接入内容表（验证标准：现有 16 个测试**一行不改**全绿 = 对拍通过）
- [x] **T5** 商店与库存协议：`C2S::{BuyItem, RequestShop}` + `S2C::{ShopList, InventoryUpdate, TradeError}` + GDScript `net_codec.gd` 编解码分支 + 新黄金字节测试（**协议变更**）— 服务端权威账本 `inventory: HashMap<pid, HashMap<item, i64>>`，击杀掉落记给 last hitter；所有失败回 TradeError（raid is over / unknown item / not for sale / insufficient coins）
- [x] **T6** 玩家数据 SQLite：rusqlite(bundled) + 自写编号迁移器（`schema_migrations` 表，第一天就有）+ `PlayerRepo` trait 隔离（10 年可换 PostgreSQL）；表：`inventory(pid,item_id,count)` / `purchases` 流水 — 写穿持久化：击杀掉落与购买在 mutate 时同步落库（data/players.db，不入 git）；跨会话库存恢复等账号系统落地后启用（读 API 已就位）
- [x] **T7** 内容热载：`RwLock<Arc<ContentTables>>` 快照交换 + 管理端点重载（不停机换表）— `content_store.rs`：swap 前先 validate（fail-closed，坏表保持旧快照）；World 每 tick 拉快照，交换在下一个 20TPS 边界生效；管理端点 `127.0.0.1:24566`（仅回环，命令 `reload [dir]` / `status`）；e2e 实测 reload 回 `ok zombies=4 items=4`
- [x] **T8** `docs/SERVER_DEV.md` 新增 §11 内容运营与商业化章；联动素材 SOP（改表→校验→CI 对拍→热载）

## 10 年不变量（改代码前必读）

1. **ID 永不复用**：物品/僵尸/活动 ID 发布即冻结；下架 = 标记 `deprecated`，不删行。
2. **线格式只增不改**：bincode 布局钉死，新消息 = 新枚举变体；黄金字节测试**永不删除、永不改期望值**（只能新增）。
3. **schema 迁移只增不改**：编号递增，已发布的迁移文件是历史档案。
4. **确定性 = 商业化公平的根基**：同 seed 必须产出同刷怪/同掉落序列；任何内容表变更必须过同 seed 对拍。
5. **会话可丢，账本不可丢**：服务器重启丢房间没问题（Hello 重开局已实现），玩家库存/购买流水必须持久化。
6. 服务端模拟保持纯函数内核：内容表数据进、S2C 出，无隐藏全局状态。

---
状态：✅ 看板清空（2026-09-09，T1-T8 全部完成）。cargo 60 全绿 = protocol 24 + server-bin 36；test_ws_codec 32 断言；e2e ws_roundtrip 16 项含商店回环与管理端点实测。运营入口：§热载 SOP（SERVER_DEV.md §11.4）/ 联动 SOP（§11.5）；管理端口 127.0.0.1:24566（reload/status）。下一步候选：账号系统与稳定身份（激活跨会话库存恢复）、purchases 消耗链路、CI 内容表对拍流水线。

## 第二阶段看板（商业化 · 客户端对接，UI 侧契约见 docs/CLIENT_API.md）

- [x] **T9** 账号身份协议：`C2S::Auth{pid,token}` + `S2C::{AuthOk{uid,name,coins}, AuthErr}`（判别值 8/12/13）+ players 表迁移 002（设备 token 免密账号，auth-or-create 幂等）+ 注册奖励 200 coin（onboarding economy：新玩家首杀前就能完成一次购买）+ 账本键写穿映射 pid→uid（**协议变更**）
- [x] **T10** 库存全量查询：`C2S::RequestInventory{pid}` + `S2C::InventorySnapshot{entries}`（判别值 9/14，按 item_id 排序）——背包/仓库页数据源
- [x] **T11** `docs/CLIENT_API.md` 客户端接口文档：C2S 0-9 / S2C 0-14 全字段、UI 分页映射（游戏/账号/商店/背包）、错误语义表、外观 skins 与通行证 battle pass 占位形状、UI 自检清单
- [ ] **T12** 外观 skins：内容表 `kind="skin"` 行 + `EquipSkin` 协议 + 购买链路复用（**协议变更**）
- [ ] **T13** 通行证 battle pass：`pass.toml` 内容表 + `RequestPass/PassState` 协议 + 领取链路（**协议变更**）
- [ ] **T14** CI 内容表对拍流水线（GitHub Actions：cargo test + godot headless 双侧对拍）

状态（二阶段）：T9-T11 完成（2026-09-09，cargo 72 全绿 = protocol 29 + server-bin 43；codec G1-G7；e2e 18 项含账号/快照回环）。T12-T14 按序推进。
