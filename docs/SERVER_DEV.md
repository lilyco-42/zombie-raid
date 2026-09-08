# 外置专用服务端调研 v2：Rust 生态 / 协议 / 迁移路径

> 目标：把现在「主机进程内」的权威模拟（`net.gd` ENet 开房模式）拆出进程，
> 换成**可独立部署的外置服务端**，客户端变成纯接入端。
> **决策更新（2026-09-08）**：实时性优先 → 服务端语言定案 **Rust**（v1 版的 Go 结论降为备选，对比数据保留在 §2）。
> 本文是调研与决策记录（design first），动手前先对齐。
> 前置阅读：`docs/NET_ARCHITECTURE.md`（现有 C/S 架构与快照格式）。

## 1. 结论（TL;DR）

| 项 | 决策 | 一句话理由 |
|---|---|---|
| 语言 | **Rust** | 无 GC 尾延迟（tick 预算确定性）；协议 crate 可同时编译进服务端与 Godot 客户端扩展（gdext）→ **协议零漂移**；renet 自带 netcode 加密鉴权 |
| 网络库（服务端） | **renet**（UDP，renet_netcode 传输层） | 引擎无关（Bevy 插件只是可选层）；通道三档可靠性正好映射我们的快照/事件模型；自带分片重组 + 加密鉴权（netcode 协议） |
| 客户端接入 v1 | **GDScript WebSocketPeer ↔ tokio-tungstenite** | 不引 GDExtension 就能联调；协议同源；裸 IP 仍走 ENet（局域网零配置不变） |
| 客户端接入 v2（可选加强） | **gdext 扩展嵌 renet 客户端**（UDP + 加密鉴权，延迟最低） | godot-rust v0.5.x 成熟可用；服务端与客户端共用同一 `protocol` crate |
| QUIC/WebTransport | **升级线保留**（quinn + web-transport-quinn） | Rust 侧是事实标准（2026-02 仍在活跃发版）；Godot 无内置，等有浏览器端/弱网需求再上 |
| 序列化 | **快照 float32 原样；事件消息 serde + bincode/postcard** | 低频可靠消息用 Rust serde 单源定义；快照本来就是二进制 |
| Bevy 服务端 | **不引入** | lightyear/bevy_replicon 只服务 Bevy 客户端，无 Godot 对接；本作服务端是状态机不是 ECS 世界 |

规模预算：单房 4 人 20 TPS + 15Hz 快照 ≈ 6 KB/s/端，tick 预算 50ms；
Rust 把 tick 耗时的**尾部**钉死（无 GC STW），1 vCPU / 2GB VPS 余量以百人计。

## 2. 候选栈对比（v1 数据保留，Go 降为备选）

| 栈 | 并发模型 | 传输/序列化 | 部署 | 结论 |
|---|---|---|---|---|
| **Rust**（renet / quinn / tokio） | 无 GC，tick 尾延迟确定；renet 自带加密鉴权 | UDP netcode / QUIC / WS 全覆盖；serde 单源协议 | 单静态二进制，musl 交叉编译 | ✅ **定案** |
| Go（gorilla/websocket） | goroutine/连接 + Hub；GC STW <1ms 但 p99 会抖 | WS 为主，QUIC 走 quic-go | 单二进制 | 备选：工程速度最快，但协议无法进 Godot 客户端，实时尾部不如 Rust 确定 |
| Node.js（Colyseus） | 单线程事件循环 | WS + Schema delta | npm 运行时 | 框架锁协议 → 不用 |
| Nakama | Go 内核 + 插件 | gRPC/WS | Postgres/Redis 全家桶 | 账号匹配都不需要 → 不用 |
| SpacetimeDB | 数据库即世界 | WS + 自动同步 | 新锐运行时 | Godot 支持弱 → 观望 |
| Agones（K8s） | 舰队编排 | 不关心 | K8s | 多服再回来看 |

## 3. Rust 生态地图（2026-09 实测活跃度）

| crate | 角色 | 状态（截至 2026-09） | 关键点 |
|---|---|---|---|
| **renet** (`lucaspoffo/renet`) | UDP 服务端/客户端网络库 | v1.1（2025-08），518 commits；bevy_renet 4.0.1（2026-03） | 通道 `Unreliable` / `ReliableOrdered{resend}` / `ReliableUnordered{resend}`；分片重组；`renet_netcode` 传输层 = netcode 协议（connect token + 加密 + 鉴权）；poll 式 `server.update(dt)` 引擎无关 |
| renet2 / bevy_renet2 | renet 社区分叉 | 0.14.0（2026-04），bevy_replicon_renet2 底座 | 分叉活跃是双保险；纯服务端用法两边 API 同形，先锁定 `renet` 1.x，需要时迁移成本低 |
| **tokio + tokio-tungstenite** | WebSocket 路径（v1 主力） | 生态标准 | 服务端 v1 用它接 GDScript `WebSocketPeer`；20 TPS 用 `tokio::time::interval` 或独立 tick 线程 |
| **quinn** | QUIC 实现 | Rust QUIC 事实标准 | 拥塞控制可选 BBR（低延迟档）；升级线的地基 |
| **web-transport-quinn** (`kixelated`) | WebTransport 封装 | 0.11.6（2026-02），约 3.7 万下载/月，moq 项目在用 | streams（可靠有序）+ datagrams（不可靠 ~MTU）正好映射事件/快照；另有 webtrans-quinn 0.5（2026-07，带 WASM 端） |
| **godot-rust gdext** | Rust ↔ Godot 4 绑定 | v0.5.5（2026-08），3.2k commits，MPL-2.0 | 支持 Godot 4.1+（运行时 ≥ API 版本即可）；可与 GDScript 混用；pre-1.0 有破坏性变更风险，锁小版本 |
| serde + bincode / postcard | 事件消息序列化 | 生态标准 | `protocol` crate 单源定义 14 消息；postcard 走 varint 更省字节；rkyv（零拷贝）暂不需要 |
| lightyear / bevy_replicon | Bevy 全家桶复制 | 活跃 | ❌ 只服务 Bevy 客户端、服务端要背整个 Bevy App —— 与 Godot 客户端无缘，排除 |

**Rust 独有卖点（Go 给不了的）**：`protocol` crate 同时被服务端二进制和 gdext 客户端扩展编译——
协议改动一处，两端编译期同时报错，**杜绝客户端/服务端协议漂移**。

## 4. 线协议 v1 = 现有 14 个 RPC 的翻译（不变）

net.gd 的 RPC 注解已写明方向、频率与可靠性，直接映射成 `protocol` crate 的消息 enum：

### 客户端 → 服务端

| 消息 | 频率 | 可靠性 | 载荷 | 来源 RPC |
|---|---|---|---|---|
| `player_state` | 15Hz | 不可靠有序 | pid, pos, yaw, speed, on_floor, crouch | `rpc_player_state` |
| `hit_zombie` | 事件 | 可靠 | net_id, dmg（服务端限频 20/s、伤害 ≤80、射程 ≤80m） | `rpc_hit_zombie` |
| `box_taken` | 事件 | 可靠 | pos（按坐标认领，先到先得） | `rpc_box_taken` |
| `report_extract` | 事件 | 可靠 | in_zone | `rpc_report_extract` |
| `report_player_died` | 事件 | 可靠 | —（全队共死） | `rpc_report_player_died` |
| `hello` | 连接时 | 可靠 | 客户端版本、协议号、种子确认 | `join_game`/`rpc_seed` 应答 |

### 服务端 → 客户端

| 消息 | 频率 | 可靠性 | 载荷 | 来源 RPC |
|---|---|---|---|---|
| `seed` | 进房/每轮 | 可靠 | seed, elapsed | `rpc_seed` |
| `zombie_states` | 15Hz | 不可靠有序 | seq + 7×N float（id,x,y,z,yaw,anim,type） | `rpc_zombie_states` |
| `net_state` | 1Hz | 可靠 | elapsed, frenzy | `rpc_net_state` |
| `raid_started` | 事件 | 可靠 | — | `rpc_raid_started` |
| `zombie_dead` | 事件 | 可靠 | net_id, pos, drop_value | `rpc_zombie_dead` |
| `remove_box` | 事件 | 可靠 | pos | `rpc_remove_box` |
| `extract_success` | 事件 | 可靠 | — | `rpc_extract_success` |
| `raid_failed` | 事件 | 可靠 | — | `rpc_raid_failed` |
| `damage_player` | 事件 | 可靠 | dmg | `rpc_damage_player` |

renet 通道配置直接对号入座：快照走 `Unreliable` 通道，其余全部 `ReliableOrdered`；
WS 路径见下方帧格式 v2（bincode 判别值兼任类型头，无需独立帧头字节）。

### WS 二进制帧格式 v2（2026-09-08 落地）

同一套 `protocol` 枚举跑两种线格式，按连接协商：

| | v1 JSON（文本帧） | v2 bincode（二进制帧） |
|---|---|---|
| 载荷 | serde externally-tagged JSON | `bincode::serialize(完整枚举)` |
| 类型头 | externally-tagged 键名 | 枚举判别值（**u32 LE**）即类型头 |
| 单元变体 | 裸字符串 `"RaidFailed"` | 仅 4 字节判别值 `07 00 00 00` |

bincode legacy 布局（黄金字节测试钉死，`protocol/src/lib.rs` golden_* 测试 ↔
`game/scripts/net_codec.gd` 逐字节镜像，python struct.pack 计算参考值）：
little-endian；判别值 u32；`Vec` 长度前缀 **u64**；bool 1 字节；f32 4 字节；
`[f32;3]` 无长度前缀连排；结构体按字段声明序、无 padding。
变体索引 = 声明序：C2S `Hello=0 …ReportPlayerDied=5`；S2C `Seed=0 …DamagePlayer=8`。

协商流程（`server-bin/main.rs` ↔ `net.gd _ws_pump`）：
1. 连接建立 → 服务器**先发 JSON 文本 Seed**（早于任何入站帧，新旧客户端通吃）；
2. 客户端 socket open 后发一帧二进制 `Hello{ver:2}`（GDScript `encode_c2s`）；
3. 服务器拦截 Hello（不进 World），`ver>=2` 置 `binary_out=true`——该连接下行
   切换 bincode；`ver:1` 客户端保持 JSON（python 冒烟验证双向兼容）；
4. 入站按帧型自动检测：Text→serde_json / Binary→`decode_c2s`（坏帧记日志丢弃）；
   广播通道携带 S2C **值**，各连接在出站侧按自身格式序列化。

## 5. 关键设计：几何留客户端，状态走网络（不变）

```
外置 Rust 服务端（authority, 20 TPS, 无 GC 抖动）
┌──────────────────────────────────────────┐
│ renet server + renet_netcode(加密鉴权)     │
│ world tick: 丧尸 AI / 刷怪 / 计时 / 校验   │
│ 可走网格 + A*（首个客户端进房时上传）        │
│ tokio-tungstenite WS 入口（v1, 同端口双栈） │
└───────────────┬──────────────────────────┘
   UDP(netcode) │ 或 WebSocket
                │ seed ──▶ 客户端确定性重建城市
                ◀── player_state 15Hz
                ──▶ zombie_states 15Hz + 可靠事件
┌───────────────┴──────────────────────────┐
│ Godot 客户端: 城市/渲染/音效/本地预测      │
│ v1: WebSocketPeer(纯 GDScript)            │
│ v2: gdext 扩展嵌 renet client(可选加强)    │
│ net.gd 只换 transport，rpc_* 调用点零改动  │
└──────────────────────────────────────────┘
```

种子协议不变：服务端掷 `raid_seed` → 客户端重建同一座城；
城市几何、导航烘焙不上网络；可走网格由首个进房客户端上传，服务端只做 A* 查询。

## 6. 迁移路径（四步，每步可独立合入）

1. ✅ **抽 transport 接口**（GDScript 侧纯重构，行为不变）：
   `net_transport.gd` 基类 + `net_transport_enet.gd` 实现；rpc_* 调用点不动。
2. ✅ **WsTransport + Rust 服务端骨架 + 权威 World 落地**（2026-09-08）：
   - `server/` Cargo workspace：`protocol` crate（14 消息 serde 枚举 + LCG64 交叉验证）
     + `server-bin`（tokio-tungstenite WS :24565，`Arc<Mutex<World>>`，20 TPS tick）；
   - World 权威模拟对齐游戏源码常量：变体表（Runner/Walker/Brute 权重 3/5/2）、
     刷怪曲线（5.0s→2.2s，max_alive 6→14，360s ramp）、追击/挥击（2.0m 起手、
     0.4s 落判、1.3s CD）、命中校验（20/s 限频、80m 射程、80 clamp、30% 掉落走 LCG）、
     团灭时钟（480s frenzy → 570s RaidFailed）；
   - GDScript 侧：`net_transport_ws.gd`（WebSocketPeer）+ net.gd `_ws_mode`
     （`join_game("ws://…")` 分支、`_dispatch_s2c` 复用 rpc_* 处理器体、send_* 包装）；
     **坑**：serde 单变体 S2C 上线是裸字符串（`"RaidFailed"`），泵需双形态解析；
   - 测试：cargo 15 个 + `tests/test_ws_codec.gd`（18 断言防漂移）
     + `tests/ws_roundtrip.gd`（真实 Godot 客户端 ↔ 真实服务器全链路）。
3. ✅ **二进制化**（2026-09-08，帧格式见 §4 v2 小节）：
   - `protocol` crate：`encode_s2c`/`decode_c2s` 集中 bincode legacy 配置，
     4 个黄金字节测试（HitZombie/PlayerState/ZombieStates/RaidFailed）钉死跨语言布局；
   - `server-bin/main.rs`：广播通道 `String`→`S2C` 值；每连接 `binary_out` 协商
     （`Hello{ver>=2}` 翻转，拦截不进 World）；入站 Text/Binary 双路解析；
   - GDScript：`net_codec.gd`（StreamPeerBuffer 编解码，产出/消费与 JSON 相同的
     字典形状 → `_dispatch_s2c` 零改动）+ `net_transport_ws.gd` `send_bytes`/`poll_frames`
     （`was_string_packet()` 分流）+ net.gd `_ws_binary`/`_ws_hello_sent` 协商状态机；
     **坑**：Godot 4.4+ WebSocketPeer 二进制发送是 `send(PackedByteArray)`——
     `send_bytes`/`send_message`/`send_packet` 均不存在（ClassDB 方法表实测）；
   - 测试：cargo 19（protocol 8 含 4 黄金 + server-bin 11）+
     `test_ws_codec.gd` 25 断言（F1-F7 黄金字节/pump 集成）+
     ws_roundtrip 端到端（服务器日志实锤 `hello ver=2 binary_out=true` +
     二进制 C2S 解码）+ python 冒烟 v1 JSON 兼容（`binary_out=false`）。
4. **两条可选升级线**（互不阻塞，按需启用）：
   - **低延迟线**：gdext 扩展嵌 renet client → UDP + netcode 加密鉴权，
     客户端延迟与加密一步到位（与现有 ENet 同为 UDP，体验对齐）；
   - **WebTransport 线**：服务端加 quinn + web-transport-quinn 监听（BBR 拥塞控制），
     为浏览器端/弱网重连预留——Godot 侧仍走 WS/UDP，不强制迁移。

遗留（不阻塞当前玩法）：箱子/战利品服务端记账（v1 只中继 RemoveBox）、
地图 SpawnPoint 数据上行（v1 玩家环外刷）、断线会话清理、pid 鉴权。

## 7. `server/` 目标布局（Cargo workspace）

```
server/
  Cargo.toml          # workspace
  protocol/
    src/lib.rs        # §4 的 14 消息 enum + serde 编解码（服务端/gdext 共用）
  server-bin/
    src/main.rs       # 监听(WS:24565 / UDP:24566) + 20 TPS tick
    src/hub.rs        # 连接生命周期 / 房间(≤4人) / 广播
    src/world.rs      # 刷怪/AI/命中校验/撤离判定
    src/walkable.rs   # 可走网格存储 + A*
  server-bin/tests/   # 同种子确定性对拍
  gdext-transport/    # （可选 v2）renet client 桥 GDScript 的 Godot 扩展
```

## 8. 明确不做的事（本阶段）

- ❌ Bevy 服务端 / lightyear / bevy_replicon（Bevy 客户端专属，无 Godot 对接）
- ❌ interest management / delta 压缩（4 人 × 14 丧尸 ≈ 6 KB/s，不值）
- ❌ rkyv 零拷贝、protobuf（serde+bincode 足够，需要再加 feature）
- ❌ 数据库持久化（stash 仍在客户端；服务端无状态，重启即恢复）
- ❌ 账号/匹配/大厅（renet_netcode 的 connect token 已覆盖鉴权起步需求）

## 9. 实时性论证（决策依据存档）

- 本作实时性画像：20 TPS tick（50ms 预算）+ 15Hz 快照 + 射击即时命中校验。
  负载下 Go 也够用——但**尾部延迟**不同：Go 的 GC STW 平时 <1ms，
  在分配压力大的 tick 会偶发抖动；Rust 无 GC，tick 耗时可证确定，
  也能安全跑比 20 TPS 更密的模拟（以后要做弹道分帧/更多实体时不用换语言）。
- Rust 额外拿到三样 Go 没有的：① 协议 crate 进 Godot（gdext）零漂移；
  ② renet_netcode 的 netcode 加密鉴权开箱即用（Go 侧要自己攒）；
  ③ QUIC/WebTransport 升级线是一等公民（quinn 生态）。
- 代价如实记录：编译时间、借用检查迭代税、gdext pre-1.0 锁版本。
  结论：实时性优先的前提下，这些代价买到的确定性值得。

## 10. 参考资料

- renet（lucaspoffo/renet）README 与 Channel/Transport API；renet2 分叉（lib.rs）
- web-transport-quinn（kixelated/web-transport-rs）docs.rs 与 DeepWiki 架构页；webtrans-quinn
- godot-rust gdext：v0.5 发布说明（2026-03）与 compatibility 文档（Godot 4.1+ 运行时规则）
- lightyear/bevy_replicon 对比（Bevy 生态定位，排除依据）
- v1 版调研（Go 选型过程与框架评估）见 git 历史：docs/SERVER_DEV.md @ e3fa560
