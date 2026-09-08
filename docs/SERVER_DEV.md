# 外置专用服务端调研：语言选型 / 协议 / 迁移路径

> 目标：把现在「主机进程内」的权威模拟（`net.gd` ENet 开房模式）拆出进程，
> 换成**可独立部署的外置服务端**，客户端变成纯接入端。
> 本文是调研与决策记录（design first），动手前先对齐。
> 前置阅读：`docs/NET_ARCHITECTURE.md`（现有 C/S 架构与快照格式）。

## 1. 结论（TL;DR）

| 项 | 决策 | 一句话理由 |
|---|---|---|
| 语言/框架 | **Go + gorilla/websocket**，手写权威循环 | 4 人房间不需要框架；单二进制部署；goroutine 并发模型天然贴合「一连接一协程 + Hub 广播」 |
| 传输层 | **WebSocket (TCP)**，保留 ENet 作局域网模式 | Godot 原生 `WebSocketPeer` 零依赖；Web 出口友好；4 人规模 TCP 重传代价可忽略 |
| 序列化 | **开发期 JSON，生产期二进制**（float32 LE 数组 + 可选 protobuf） | 现有丧尸快照 `PackedFloat32Array` 本来就是二进制协议，JSON 只用于调试肉眼可读 |
| QUIC | **不做** | Godot 未内置（需 GDExtension 封 msquic/quiche）；收益（弱网丢包下的队头阻塞消除）对 4 人合作 PVE 几乎为零 |
| 服务端框架（Colyseus/Nakama 等） | **不引入** | 房间管理/匹配/账号体系目前都不需要；引入即背上运行时与运维成本 |
| 权威模型 | **照搬现有 20 TPS 服务端权威**，net.gd 的 14 个 RPC 就是线协议 v1 | 已上线并测试过的协议不需要重设计，只需要「翻译」 |

规模预算：1 vCPU / 2GB VPS（≈¥30-70/月）可跑 30-50 人同服
（本作实际负载：20 TPS tick + 15Hz 快照 ≈ 6 KB/s/客户端，单房 4 人）。

## 2. 候选栈对比

| 栈 | 并发模型 | 传输/序列化 | 部署 | 与 Godot 契合 | 结论 |
|---|---|---|---|---|---|
| **Go**（gorilla/websocket 或 coder/websocket） | goroutine/连接 + channel Hub 广播；`time.Ticker` 50ms 驱动 20 TPS | WS；JSON/protobuf 均成熟 | 单静态二进制，scp 即部署 | `WebSocketPeer` 直连；协议翻译直观 | ✅ **选它** |
| **Rust**（Renet + Bevy / quinn QUIC） | ECS + 无 GC 抖动 | Renet 走 UDP + bincode；quinn 提供 QUIC | 单二进制 | Renet 无官方 Godot 绑定，协议要自桥 | 性能上限最高，但对 4 人房是杀鸡用牛刀，且迭代成本（借用检查）高 → 备选 |
| **Node.js**（Colyseus） | 单线程事件循环 + 房间 | WS + Schema 自动 delta 压缩 | `npm` 运行时 + 监控面板 | 客户端有非官方 Godot SDK，质量参差 | 原型最快，但 Schema 序列化反向锁死协议；引入框架违背「薄依赖」偏好 → 不用 |
| **Nakama** | Go 内核 + 插件 | gRPC/WS | Postgres/CockroachDB + Redis 全家桶 | 有官方 Godot SDK | 账号/好友/排行/匹配一应俱全——本作现在**都不需要** → 不用 |
| **SpacetimeDB** | 「数据库即世界」 | WS + 自动状态同步 | 新锐运行时 | C#/Rust 客户端，Godot 支持弱 | 理念超前但生态早期，赌不起 → 观望 |
| **Agones**（K8s） | 游戏服生命周期编排 | 不关心 | K8s 集群 | 无关 | 单服都还没部署就上编排是负 ROI → 多服舰之后再回来看 |
| 托管（Photon/PlayFab） | — | — | 云服务 | — | 付费 + 锁定 + 数据出海问题 → 不用 |

## 3. QUIC / WebTransport 评估（正面回答）

- **Godot 4.7 内置网络**：ENet（UDP）、WebSocketPeer（TCP）、WebRTC（P2P/DTLS）。
  **没有 QUIC/WebTransport**。要上 QUIC 只能：GDExtension 封 msquic/quiche/picoquic，
  或自编译引擎模块——维护成本一次买断。
- **QUIC 的真实收益**：流级复用消除队头阻塞、0-RTT 重连、连接迁移（切 Wi-Fi 不掉线）。
  这三项对 **4 人合作 PVE + 15Hz 快照**的体验增益接近 0：我们的快照本来就走
  unreliable_ordered，丢一帧下一帧就覆盖；掉线重连也可以靠「重新拉种子重建」兜底。
- **何时重新评估**：① 做 100+ 人大厅；② 手机弱网差评集中在断线重连；
  ③ Godot 官方合入 WebTransport（届时迁移成本 = 换 transport 实现，见 §5）。

## 4. 线协议 v1 = 现有 14 个 RPC 的翻译

net.gd 里的 RPC 注解已经写明了方向、频率与可靠性，直接映射成消息类型：

### 客户端 → 服务端

| 消息 | 频率 | 可靠性 | 载荷 | 来源 RPC |
|---|---|---|---|---|
| `player_state` | 15Hz | 不可靠有序 | pid, pos, yaw, speed, on_floor, crouch | `rpc_player_state` |
| `hit_zombie` | 事件 | 可靠 | net_id, dmg（服务端限频 20/s、伤害 ≤80、射程 ≤80m） | `rpc_hit_zombie` |
| `box_taken` | 事件 | 可靠 | pos（服务端按坐标认领，先到先得） | `rpc_box_taken` |
| `report_extract` | 事件 | 可靠 | in_zone | `rpc_report_extract` |
| `report_player_died` | 事件 | 可靠 | —（全队共死） | `rpc_report_player_died` |
| `hello` | 连接时 | 可靠 | 客户端版本、种子确认 | `join_game`/`rpc_seed` 应答 |

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

二进制化路径（生产期）：`zombie_states` 直接沿用 float32 数组；
其余低频可靠消息 JSON 起步，量大了再上 protobuf（`.proto` 文件放 `server/protocol/`，
Godot 侧用 `godotobuf` 类插件或手写 varint 编解码——先不做）。

## 5. 关键设计：几何留客户端，状态走网络

与现有架构完全一致，外置服务端只是把「主机」换成「无头进程」：

```
外置 Go 服务端（authority, 20 TPS）
┌──────────────────────────────────────────┐
│ world tick: 丧尸 AI / 刷怪 / 计时 / 校验   │
│ 可走网格 + A*（首个客户端进房时上传）        │   ← 唯一新增：服务端路径规划数据源
│ Hub: 连接管理 / 房间(4人) / 广播           │
└───────────────┬──────────────────────────┘
     WebSocket  │ seed ──▶ 客户端确定性重建城市
                ◀── player_state 15Hz
                ──▶ zombie_states 15Hz + 可靠事件
┌───────────────┴──────────────────────────┐
│ Godot 客户端: 城市/渲染/音效/本地预测      │
│ net.gd 只换 transport，rpc_* 调用点零改动  │
└──────────────────────────────────────────┘
```

种子协议不变：服务端掷 `raid_seed` → 客户端重建同一座城；
城市几何、导航烘焙、贴图**不上网络**。可走网格（bool 二维数组，压缩后几十 KB）
由首个进房客户端上传，服务端只做 A* 查询——避免服务端复刻 CityBuilder。

## 6. 迁移路径（四步，每步可独立合入）

1. **抽 transport 接口**（纯重构，行为不变）：
   net.gd 内定义 `NetTransport`（`connect/start_host/send_raw/poll/disconnected` 信号），
   现有 ENet 逻辑包成 `EnetTransport`；rpc_* 收发走接口。
2. **加 WsTransport**：Godot `WebSocketPeer` 实现（内置，零依赖）。
   `join_game("ws://host:24565")` 走 WS，裸 IP 仍走 ENet（局域网零配置不变）。
3. **Go 服务端骨架**：`server/` 实现线协议 v1（先用 JSON），
   丧尸 AI 从 `zombie.gd`/`raid_manager.gd` 移植成 Go（状态机简单，重逻辑轻表现）；
   `go test` 对拍 GDScript 单测（同一种子 → 同一刷怪序列）。
4. **生产化**：float32 二进制快照、systemd 部署、`--server` 进程内无头模式退役
   （被外置服务端替代，保留作为调试用途）。

## 7. `server/` 目标布局（Go）

```
server/
  go.mod
  main.go          # :24565 监听(WS), 启动 tick
  hub.go           # 连接生命周期 / 房间(≤4人) / 广播
  world.go         # 20 TPS 权威循环: 刷怪/AI/命中校验/撤离判定
  walkable.go      # 可走网格存储 + A*
  protocol/
    messages.go    # §4 的 14 消息 struct + 编解码
    (proto 可选)
  world_test.go    # 同种子确定性对拍
```

## 8. 明确不做的事（本阶段）

- ❌ QUIC/WebTransport（§3，重新评估条件已列）
- ❌ interest management / delta 压缩（4 人 × 14 丧尸 ≈ 6 KB/s，不值）
- ❌ 数据库持久化（stash 仍在客户端；服务端无状态，重启即恢复）
- ❌ 账号/匹配/大厅（token 白名单起步即可，真需要再评估 Nakama）
- ❌ 移动端断线重连的 0-RTT 优化（现在的「重拉种子重建」够用）

## 9. 参考资料

- Godot 高层多人 API 与 WebSocketPeer：docs.godotengine.org（Networking）
- gorilla/websocket（Go 事实标准，已恢复维护）/ coder(websocket) fork
- Colyseus 文档（房间模型与 Schema delta —— 作为「如果哪天想要框架」的对照）
- Renet / quinn（Rust 备选）；Nakama（全家桶备选）；Agones（K8s 编排备选）
