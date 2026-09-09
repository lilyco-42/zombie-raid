# CLIENT_API.md — 客户端 UI 对接手册（服务端 → UI 侧）

> **给客户端/UI AI**：本文是 UI 侧消费服务端的唯一权威契约。服务端保证
> 本文所有形状稳定（协议只增不改，见 §1.3）；你按形状画 UI、连信号即可，
> **不要自己写编解码**——`game/scripts/net_codec.gd` + `net.gd` 已带全部
> 分支与信号（服务端 AI 维护），UI 层只管 `connect()` 与布局。
>
> 状态：✅ 全部已实现并测试（2026-09-09）。§7 的外观/通行证是**占位形状**，
> 服务端按清单实现，UI 可先出界面。

---

## 1. 连接与握手

### 1.1 地址与生命周期

```
ws://<host>:24565        游戏主连接（唯一连接，UI 与战斗共用）
127.0.0.1:24566          管理端口（仅运维热载，UI 永远不碰）
```

生命周期：`join_game(url)` → 连接成功 → 自动发二进制 `Hello{ver:2}` →
收 JSON `Seed{seed,elapsed}`（握手完成，进入 raid）→ 之后全部走 bincode。

### 1.2 UI 侧调用入口（net.gd 现成 API）

| UI 动作 | net.gd 调用 | 收到的信号 |
|---|---|---|
| 登录（账号页） | `net.send_auth(token)` | `auth_ok(uid,name,coins)` / `auth_error(reason)` |
| 打开商店 | `net.send_request_shop()` | `shop_received(entries)` |
| 购买 | `net.send_buy_item(item_id)` | `inventory_update(pid,item,count)` / `trade_error(reason)` |
| 打开背包/仓库 | `net.send_request_inventory()` | `inventory_snapshot(entries)` |
| 开局/战斗 | `net.join_game(...)` | `seed_received` / `raid_failed_net` / `extract_success_net` |

`net.gd` 信号总表（UI 全部从这些进）：
`seed_received` `shop_received` `inventory_update` `trade_error`
`auth_ok` `auth_error` `inventory_snapshot` `raid_failed_net`
`extract_success_net`

### 1.3 协议铁律（UI 侧须知）

- 判别值**只增不改**：S2C 0-14 已占，未知变体会打 `[net] unknown S2C variant`
  并跳过——UI 收到未知变体不会崩，直接忽略。
- 字段形状冻结：`InventoryUpdate.count` 永远是 i64（可为负=扣除），
  `ShopList.entries` 永远是 `[[item_id, price], ...]`。

---

## 2. C2S 全清单（客户端 → 服务端，判别值 u32 LE）

| # | 变体 | 字段 | 何时发 |
|---|---|---|---|
| 0 | `Hello {ver}` | ver:u32（固定 2） | 自动（join 后） |
| 1 | `PlayerState {pid,pos,yaw,speed,on_floor,crouch}` | pos:[f32;3] | 15Hz（战斗中自动） |
| 2 | `HitZombie {pid,net_id,dmg}` | dmg:f32 | 开枪命中时 |
| 3 | `BoxTaken {pos}` | pos:[f32;3] | 拾取物资箱 |
| 4 | `ReportExtract {in_zone}` | in_zone:bool | 进/出撤离区 |
| 5 | `ReportPlayerDied` | — | 玩家死亡 |
| 6 | `BuyItem {pid,item_id}` | item_id:String | 商店点击购买 |
| 7 | `RequestShop` | — | 打开商店页 |
| 8 | `Auth {pid,token}` | token:String | **账号页登录（进 raid 后尽快发）** |
| 9 | `RequestInventory {pid}` | — | 打开背包/仓库页 |

`pid` = 客户端会话内自报 id（v1 信任模型），`net.gd` 自动带 `_ws_pid`，
**UI 层不用管**。

## 3. S2C 全清单（服务端 → 客户端）

| # | 变体 | 字段 | UI 消费方 |
|---|---|---|---|
| 0 | `Seed {seed,elapsed}` | seed:u64, elapsed:f32 | 主界面→对局 |
| 1 | `ZombieStates {seq,ents}` | ents:[{id,pos,yaw,anim,ztype}] | HUD/战斗 |
| 2 | `NetState {elapsed,frenzy}` | — | HUD 时钟 |
| 3 | `RaidStarted` | — | HUD |
| 4 | `ZombieDead {net_id,pos,drop_value}` | drop_value:i32 | 击杀特效/掉落 |
| 5 | `RemoveBox {pos}` | — | 场景 |
| 6 | `ExtractSuccess` | — | 结算页（胜） |
| 7 | `RaidFailed` | — | 结算页（败） |
| 8 | `DamagePlayer {pid,dmg}` | — | HUD 血条（pid 过滤已内置） |
| 9 | `ShopList {entries}` | entries:[(String,u32)] | **商店页** |
| 10 | `InventoryUpdate {pid,item_id,count}` | count:i64 | **背包/钱包增量** |
| 11 | `TradeError {pid,reason}` | reason:String | **商店错误弹窗** |
| 12 | `AuthOk {uid,name,coins}` | — | **账号页登录成功态** |
| 13 | `AuthErr {reason}` | — | **账号页错误提示** |
| 14 | `InventorySnapshot {entries}` | entries:[(String,i64)] | **背包/仓库页全量** |

---

## 4. 分页 → 协议流程映射（主界面 / 账号 / 商店 / 背包）

### 4.1 主界面「游戏」分页

```
join_game(url) → 收 Seed → 进对局 → 战斗消息(1,2,3,4,5,6,7,8)
死亡 → ReportPlayerDied → RaidFailed → 结算页
撤离 → ReportExtract{true} → ExtractSuccess → 结算页（可带掉落清单）
再战 → join_game() 重新来（服务端自动开新 seed）
```

### 4.2 「账号」分页（T9 设备免密账号）

1. 首次启动：客户端生成 token = 随机 GUID，存 `user://account.token`
   （**UI 侧职责**：生成与持久化；服务端只收字符串）。
2. 进 raid 后尽快 `send_auth(token)`。
3. 收 `AuthOk{uid,name,coins}` → 账号页显示：
   - `name`：服务端自动起的名（`survivor#0001` 格式），UI 直接展示；
     （改名接口未开——占位 §7.3）
   - `coins`：登录时点余额，之后以 `InventoryUpdate(item_id=="coin")` 增量为准。
4. 收 `AuthErr{reason}`：`invalid token`（token 空/超 64 字节）→
   UI 提示重新生成 token 重试；`persistence unavailable` → 服务端无持久层
   （测试环境），UI 显示"离线模式"。

**注册奖励**：新账号自动获得 **200 coin**（够买一个绷带 120）——
新玩家第一局就能体验商店购买循环。UI 可在首登时弹"欢迎礼包"。

### 4.3 商店分页（商业化主路径）

```
打开商店 → send_request_shop() → shop_received(entries)
entries = [["bandage",120], ["ammo_box",250], ...]   # (item_id, 价格)
点击购买 → send_buy_item(item_id)
  成功 → 两条 inventory_update：第一条是 coin 扣款(负增量)，第二条是物品+1
  失败 → trade_error(reason)：
    "raid is over"        → 对局已结束（UI 关商店回结算）
    "unknown item 'X'"    → 客户端数据过期（重新拉 ShopList）
    "not for sale"        → 该商品不可购（UI 置灰逻辑以此兜底）
    "insufficient coins"  → 余额不足（引导：先去打钱）
```

UI 注意：价格与可购状态以 `ShopList` 为准（服务端内容表权威），
**不要在客户端硬编码价格**。

### 4.4 背包 / 仓库分页

```
打开 → send_request_inventory() → inventory_snapshot(entries)
entries = [["coin",200], ["bandage",1], ...]   # (item_id, 数量)，按 id 排序
之后任意变动（购买/击杀掉落/消耗）都会推 inventory_update(pid,item,±delta 后的绝对值)
```

- `InventoryUpdate.count` 是**该物品的当前绝对数量**（不是增量），UI 直接覆盖显示。
- 空快照合法（真的什么都没有）。
- 数量是 i64：正常范围 ≥ 0；看到负数是协议层 bug，上报服务端 AI。

---

## 5. 字节编码规则（参考，UI 层通常不需要）

- 容器：bincode legacy。判别值 u32 LE；枚举外层 = `判别值 + 字段`。
- String：`u64 LE 字节长 + raw UTF-8`（**不是** Godot 的 u16 前缀 put_utf8_string）。
- 数值：u32/i64/f32 全部 LE；i64 直接位模式（GDScript `get_u64()` 天然补码）。
- bool：1 字节。
- 黄金样例（Rust `server/protocol/src/lib.rs` golden_* 与
  `tests/test_ws_codec.gd` F/G 系列双侧钉死，改动即 CI 红）：
  - `BuyItem{pid:357,"bandage"}` = `06 00 00 00 65 01 00 00 07 00 00 00 00 00 00 00 62 61 6e 64 61 67 65`
  - `Auth{pid:357,"abc12345"}` = 24 字节（G1）
  - `AuthOk{1,"survivor#0001",1250}` = 37 字节（G3）

---

## 6. 边界与错误语义速查

| 场景 | 服务端行为 | UI 应对 |
|---|---|---|
| 未登录就击杀/购买 | 记会话账本（本次连接有效），不持久 | 账号页提示"未登录，进度不会保存" |
| 登录后会话与持久账本冲突 | 持久值覆盖会话（Auth=恢复存档） | 登录应尽早（进 raid 即发），登录前收益不保证 |
| 同 token 重复登录 | 同一 uid（幂等），不产生新号 | — |
| token 换设备 | 同 token 即同账号 | UI 把 `user://account.token` 当账号本体 |
| 商店购买后 RaidFailed | 购买已入账，持久有效 | 结算页仍显示新余额 |
| 断线重连 | 新连接新 pid，需重新 Auth | UI 在 reconnect 后自动重发 send_auth |

## 7. 占位形状（UI 可先出界面，服务端按此实现）

### 7.1 外观（skins）——预告字段
- 内容表将加 `kind = "skin"` 的 items 行；`ShopList` 自然带出。
- 购买复用 `BuyItem`（钱包扣款一致）；装备接口预告：
  `C2S::EquipSkin { pid, item_id }` → `S2C::SkinEquipped { pid, item_id }`。
- UI 建议：商店加"外观"子页，格子用 item_id 对应资源（CDN 资产，服务端只发 ID）。

### 7.2 通行证（battle pass）——预告字段
- 内容表将加 `pass.toml`：赛季 id、等级门槛（经验/任务）、每级奖励表。
- 预告：`C2S::RequestPass { pid }` → `S2C::PassState { season, level, xp, claims:Vec<(u32, String)> }`；
  领取复用购买回执模式。
- UI 建议：通行证子页 = 纵向等级轨 + 领取按钮（置灰条件：level 不足或已领）。

### 7.3 其他已排期（UI 可预留入口，勿发未实现消息）
- 改名（`Rename { pid, name }`）、第二张关卡蓝图的选择接口、账号注销。
- **纪律**：UI 不得发送本文未列出的 C2S 变体——服务端对未知变体会断连。

## 8. UI 侧自检清单（提交前）

1. `tests/test_ws_codec.gd`（godot headless）全绿——不动 F/G 断言。
2. `tests/ws_roundtrip.gd` 全绿——含商店、账号、背包回环。
3. 价格/数量渲染只用 S2C 字段，零硬编码。
4. `AuthErr`/`TradeError` 的 reason 直接展示给玩家（已按运营文案写）。
