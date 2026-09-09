extends Node
## Net — co-op multiplayer autoload (ENet, host-authoritative).
## One player hosts (becomes the authority for zombies, loot, timers);
## up to 3 clients join by IP. The world is procedurally built from a
## shared seed so every peer builds identical geometry; runtime events
## (spawns, kills, pickups, extraction) are RPC'd by the host.
##
## WS mode (_ws_mode): join_game("ws://host:24565") links to the Rust
## dedicated server instead (docs/SERVER_DEV.md §6 step ③). The raw
## WebSocketPeer is not a MultiplayerAPI — C2S/S2C JSON dicts flow through
## the send_* wrappers and _dispatch_s2c; the rpc_* handler bodies are
## reused so both links share one client-side state machine.
##
## Death of ANY player fails the raid for the team (Lethal Company rule).

signal peer_joined(peer_id: int)
signal peer_left(peer_id: int)
signal raid_started_net
signal raid_failed_net
signal extract_success_net
signal lobby_changed
signal join_failed(reason: String)
signal seed_received
# T5 commercialization: the server-authoritative shop/inventory channel.
# entries arrive as [[item_id, price], ...] - ready for the shop UI grid.
signal shop_received(entries: Array)
signal inventory_update(pid: int, item_id: String, count: int)
signal trade_error(reason: String)
signal auth_ok(uid: int, name: String, coins: int)
signal auth_error(reason: String)
signal inventory_snapshot(entries: Array)

const PORT := 24565
const MAX_PEERS := 3            # + host = 4 players
const TICK_RATE := 20.0         # authority heartbeat — Minecraft runs 20 TPS
const SNAPSHOT_RATE := 15.0     # entity snapshot broadcast (Hz)
const INTERP_SNAPSHOTS := 3     # clients render entities N snapshots behind (MC lerpSteps)
const STATE_DT := 1.0 / 15.0    # player state broadcast (15 Hz)
const NETSTATE_DT := 1.0        # global clock broadcast (1 Hz)
const MAX_HIT_RATE := 20.0      # server-side anti-cheat: hits per second per peer
const MAX_HIT_DAMAGE := 80.0    # damage clamp on client hit reports
const MAX_HIT_RANGE := 80.0     # distance clamp shooter -> zombie

const RemoteAvatarScript := preload("res://game/scripts/remote_avatar.gd")
# Link-layer is swappable (docs/SERVER_DEV.md §6 step ①): ENet today,
# WsTransport (Rust server) plugs in here without touching rpc_* call sites.
const TransportScript := preload("res://game/scripts/net_transport_enet.gd")
const WsTransportScript := preload("res://game/scripts/net_transport_ws.gd")
# Binary codec for wire format v2 (layout pinned by server/protocol golden
# byte tests; net_codec.gd must mirror them exactly)
const NetCodec := preload("res://game/scripts/net_codec.gd")

var online := false
var hosting := false
var raid_active := false
var raid_seed := -1             # seed of the currently built world (both sides)
var pending_seed := -1          # client: seed to apply on next world load
var pending_elapsed := 0.0      # client: raid clock to restore when joining late
var world: Node3D               # registered by world_raid._ready
var _transport = null           # NetTransport instance while online
var _ws_mode := false           # linked to the Rust dedicated server (raw WS)
var _ws_pid := 0                # self-chosen id in WS mode (server-trusted v1)
var _ws_binary := false         # v2 negotiated: bincode frames both ways
var _ws_hello_sent := false     # the Hello{ver:2} upgrade, flushed once open

var _next_net_id := 1
var _tick_acc := 0.0            # fixed-tick accumulator (server only)
var _snap_seq := 0              # monotonic snapshot sequence number
var _zombie_t := 0.0
var _netstate_t := 0.0
var _hit_times := {}            # peer_id -> last accepted hit (server validation)
var _avatars := {}              # peer_id -> RemoteAvatar
var _upnp: Object = null        # UPnP instance; absent in some builds (web)

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	multiplayer.peer_connected.connect(_on_peer_connected)
	multiplayer.peer_disconnected.connect(_on_peer_disconnected)
	multiplayer.connected_to_server.connect(_on_connected_ok)
	multiplayer.connection_failed.connect(_on_connection_failed)
	multiplayer.server_disconnected.connect(_on_server_gone)

# ---------------------------------------------------------------- lobby ---

func host_game() -> bool:
	_ws_mode = false
	_transport = TransportScript.new()
	var err: int = _transport.start_host(PORT, MAX_PEERS)
	if err != OK:
		_transport = null
		return false
	_transport.attach(self)
	online = true
	hosting = true
	_next_net_id = 1
	_hit_times.clear()
	# "Open to LAN" style: the world may already be running solo — keep it.
	# Mid-raid hosting: restore the raid state and hand out ids retroactively.
	if world != null and world.get("manager") != null:
		raid_active = world.manager.elapsed > 0.0
		for z in world.get_tree().get_nodes_in_group("zombie"):
			if int(z.get("net_id")) <= 0:
				z.net_id = next_net_id()
				z.name = "Z_%d" % int(z.net_id)
	else:
		raid_active = false
	_upnp_setup(PORT)
	lobby_changed.emit()
	return true

func join_game(ip: String) -> bool:
	# ws:// or wss:// links to the Rust dedicated server (WS mode)
	if ip.begins_with("ws://") or ip.begins_with("wss://"):
		return _ws_join(ip)
	var peer := ENetMultiplayerPeer.new()
	var err := peer.create_client(ip, PORT)
	if err != OK:
		return false
	multiplayer.multiplayer_peer = peer
	online = true
	hosting = false
	lobby_changed.emit()
	return true

func _ws_join(url: String) -> bool:
	var t = WsTransportScript.new()
	if t.join(url) != OK:
		return false
	_transport = t
	online = true
	hosting = false
	_ws_mode = true
	_ws_binary = false
	_ws_hello_sent = false
	# v1 trust model: the client picks its id and the server trusts it
	# (netcode auth lands with renet in a later step).
	_ws_pid = 2 + randi() % 998
	lobby_changed.emit()
	return true

func leave() -> void:
	if _ws_mode and _transport != null:
		_transport.close()
		_transport = null
	if multiplayer.multiplayer_peer != null:
		multiplayer.multiplayer_peer.close()
	multiplayer.multiplayer_peer = null
	online = false
	hosting = false
	_ws_mode = false
	_ws_binary = false
	_ws_hello_sent = false
	raid_active = false
	pending_seed = -1
	pending_elapsed = 0.0
	raid_seed = -1
	_clear_avatars()
	lobby_changed.emit()

func is_host() -> bool:
	if _ws_mode:
		return false  # the Rust server owns authority in WS mode
	return online and (not hosting or multiplayer.is_server())

func my_id() -> int:
	if _ws_mode:
		return _ws_pid
	return multiplayer.get_unique_id() if online else 1

func next_net_id() -> int:
	_next_net_id += 1
	return _next_net_id

func _upnp_setup(port: int) -> void:
	# Best-effort port mapping so friends can join over the internet.
	# UPnP is a build-time optional module (missing on web) — resolve via
	# ClassDB so the script compiles everywhere.
	if not ClassDB.class_exists("UPnP"):
		return
	_upnp = ClassDB.instantiate("UPnP")
	if _upnp.discover() != OK or _upnp.get_gateway() == null:
		return
	_upnp.add_port_mapping(port, port, "zombie-raid", "UDP")

# ------------------------------------------------------------ callbacks ---

func _on_peer_connected(pid: int) -> void:
	if hosting:
		# Send the world seed (+ raid clock if the raid already runs)
		var elapsed := 0.0
		if world != null and world.get("manager") != null:
			elapsed = world.manager.elapsed
		rpc_id(pid, "rpc_seed", raid_seed, elapsed)
	_ensure_avatar(pid)
	peer_joined.emit(pid)
	lobby_changed.emit()

func _on_peer_disconnected(pid: int) -> void:
	_hit_times.erase(pid)
	_remove_avatar(pid)
	peer_left.emit(pid)
	lobby_changed.emit()

func _on_connected_ok() -> void:
	pass  # wait for rpc_seed from the host

func _on_connection_failed() -> void:
	online = false
	hosting = false
	join_failed.emit("connection failed")

func _on_server_gone() -> void:
	leave()

# ------------------------------------------------- local player feeding ---

func push_player_state(pos: Vector3, body_yaw: float, speed: float, on_floor: bool, crouch: bool) -> void:
	if not online:
		return
	if _ws_mode:
		_ws_send({"PlayerState": {"pid": _ws_pid, "pos": [pos.x, pos.y, pos.z],
			"yaw": body_yaw, "speed": speed, "on_floor": on_floor, "crouch": crouch}})
		return
	rpc("rpc_player_state", my_id(), pos, body_yaw, speed, on_floor, crouch)

# ------------------------------------------------------------ per-frame ---

func _process(delta: float) -> void:
	if _ws_mode:
		# pump the raw socket even while world == null — the wait overlay
		# must still receive Seed and (once built) snapshots
		_ws_pump(delta)
		return
	if not online or world == null:
		return
	if raid_active and is_host():
		# Minecraft-style fixed 20 TPS authority heartbeat: gameplay decisions
		# are quantized to ticks; snapshots ride the same loop.
		_tick_acc += delta
		var tick_dt := 1.0 / TICK_RATE
		if _tick_acc > tick_dt * 10.0:
			_tick_acc = tick_dt * 10.0  # stall guard: never sprint-catch-up
		while _tick_acc >= tick_dt:
			_tick_acc -= tick_dt
			_server_tick()

func _server_tick() -> void:
	_zombie_t += 1.0 / TICK_RATE
	if _zombie_t >= 1.0 / SNAPSHOT_RATE:
		_zombie_t = 0.0
		_snap_seq += 1
		_broadcast_zombie_states()
	_netstate_t += 1.0 / TICK_RATE
	if _netstate_t >= 1.0:
		_netstate_t = 0.0
		var mgr = world.get("manager")
		if mgr != null:
			rpc("rpc_net_state", mgr.elapsed, mgr._frenzy)

# ------------------------------------------------------ zombie broadcast ---

func _broadcast_zombie_states() -> void:
	## Snapshot layout: [seq, then 7 floats per zombie: id,x,y,z,yaw,anim,type]
	var arr := PackedFloat32Array()
	arr.append(float(_snap_seq))
	for z in world.get_tree().get_nodes_in_group("zombie"):
		if int(z.get("net_id")) <= 0:
			continue
		if z.is_dead():
			continue
		var speed := Vector3(z.velocity.x, 0, z.velocity.z).length()
		var code := 2 if speed > 0.5 else 1
		if int(z.get("state")) == 3:  # zombie.gd State.ATTACK
			code = 4
		var model_node = z.get("model")
		var yaw: float = model_node.global_rotation.y if model_node != null else 0.0
		arr.append_array(PackedFloat32Array([
			float(z.net_id), z.global_position.x, z.global_position.y, z.global_position.z,
			yaw, float(code), float(z.get("ztype"))]))
	rpc("rpc_zombie_states", arr)

# ------------------------------------------------------- ws transport -----

func _ws_send(msg: Dictionary) -> void:
	if _transport != null and _ws_mode:
		if _ws_binary:
			_transport.send_bytes(NetCodec.encode_c2s(msg))
		else:
			_transport.send_text(JSON.stringify(msg))

func _ws_pump(_delta: float) -> void:
	if _transport == null:
		return
	# Wire format v2 upgrade: once the socket opens, flush one binary
	# Hello{ver:2} — the server flips this connection's downlink to bincode.
	# The handshake Seed always arrives first as JSON text (we read it with
	# the JSON path below), so both formats interleave safely.
	if not _ws_hello_sent and _transport.is_open():
		_ws_hello_sent = true
		_ws_binary = true
		_transport.send_bytes(NetCodec.encode_c2s({"Hello": {"ver": 2}}))
	for frame in _transport.poll_frames():
		if frame is PackedByteArray:
			var decoded: Dictionary = NetCodec.decode_s2c(frame)
			for variant in decoded:
				_dispatch_s2c(String(variant), decoded[variant])
		else:
			var parsed: Variant = JSON.parse_string(String(frame))
			if parsed is Dictionary:
				for variant in parsed:
					_dispatch_s2c(String(variant), parsed[variant])
			elif parsed is String:
				# serde serializes unit variants (RaidFailed/ExtractSuccess/
				# RaidStarted) as bare JSON strings on the wire
				_dispatch_s2c(parsed, null)
	if _transport.is_closed():
		_transport = null
		_ws_mode = false
		print("[net] ws server gone")
		leave()

func _dispatch_s2c(variant: String, d: Variant) -> void:
	## One S2C JSON frame from the Rust server -> the matching rpc_* body,
	## so ENet and WS clients share a single state machine.
	match variant:
		"Seed":
			rpc_seed(int(d["seed"]), float(d["elapsed"]))
		"ZombieStates":
			rpc_zombie_states(_ws_zombie_states_arr(d))
		"NetState":
			rpc_net_state(float(d["elapsed"]), bool(d["frenzy"]))
		"RaidStarted":
			rpc_raid_started()
		"ZombieDead":
			var p: Array = d["pos"]
			rpc_zombie_dead(int(d["net_id"]), Vector3(p[0], p[1], p[2]), int(d["drop_value"]))
		"RemoveBox":
			var p: Array = d["pos"]
			rpc_remove_box(Vector3(p[0], p[1], p[2]))
		"ExtractSuccess":
			rpc_extract_success()
		"RaidFailed":
			rpc_raid_failed()
		"DamagePlayer":
			# broadcast channel: a zombie hit YOUR body — ignore other pids
			if int(d["pid"]) == _ws_pid:
				rpc_damage_player(float(d["dmg"]))
		"ShopList":
			shop_received.emit(d["entries"])
		"InventoryUpdate":
			inventory_update.emit(int(d["pid"]), String(d["item_id"]), int(d["count"]))
		"TradeError":
			trade_error.emit(String(d["reason"]))
		"AuthOk":
			auth_ok.emit(int(d["uid"]), String(d["name"]), int(d["coins"]))
		"AuthErr":
			auth_error.emit(String(d["reason"]))
		"InventorySnapshot":
			inventory_snapshot.emit(d["entries"])
		_:
			print("[net] unknown S2C variant: %s" % variant)

func _ws_zombie_states_arr(d: Dictionary) -> PackedFloat32Array:
	## Rust sends {"ZombieStates":{"seq":N,"ents":[{id,pos,yaw,anim,ztype}…]}}.
	## Rebuild the ENet wire shape: [seq, id,x,y,z,yaw,anim,ztype] * N.
	var arr := PackedFloat32Array()
	arr.append(float(int(d["seq"])))
	for e in d["ents"]:
		var p: Array = e["pos"]
		arr.append_array(PackedFloat32Array([
			float(int(e["id"])),
			float(p[0]), float(p[1]), float(p[2]),
			float(e["yaw"]),
			float(int(e["anim"])),
			float(int(e["ztype"])),
		]))
	return arr

# ---- WS send wrappers: the client->server counterparts of the rpc_* ------
# call sites. In ENet mode they forward to the same rpc (one code path for
# callers, zero behavior change); in WS mode they emit protocol JSON.

func send_hit_zombie(net_id: int, dmg: float) -> void:
	if not online:
		return
	if _ws_mode:
		_ws_send({"HitZombie": {"pid": _ws_pid, "net_id": net_id, "dmg": dmg}})
	else:
		rpc("rpc_hit_zombie", net_id, dmg)

func send_box_taken(pos: Vector3) -> void:
	if not online:
		return
	if _ws_mode:
		_ws_send({"BoxTaken": {"pos": [pos.x, pos.y, pos.z]}})
	else:
		rpc("rpc_box_taken", pos)

func send_extract(in_zone: bool) -> void:
	if not online:
		return
	if _ws_mode:
		_ws_send({"ReportExtract": {"in_zone": in_zone}})
	else:
		rpc("rpc_report_extract", in_zone)

func send_player_died() -> void:
	if not online:
		return
	if _ws_mode:
		_ws_send({"ReportPlayerDied": null})
	else:
		rpc("rpc_report_player_died")

# ---- T5 shop: server-authoritative commerce (WS-mode only; the ENet
# host has no Rust ledger behind it, so those calls are no-ops there) ------

func send_buy_item(item_id: String) -> void:
	if not online:
		return
	if _ws_mode:
		_ws_send({"BuyItem": {"pid": _ws_pid, "item_id": item_id}})

func send_request_shop() -> void:
	if not online:
		return
	if _ws_mode:
		_ws_send({"RequestShop": null})

# ---- T9/T10 account: device-token sign-in + full bag dump (WS-only) ----

func send_auth(token: String) -> void:
	if not online:
		return
	if _ws_mode:
		_ws_send({"Auth": {"pid": _ws_pid, "token": token}})

func send_request_inventory() -> void:
	if not online:
		return
	if _ws_mode:
		_ws_send({"RequestInventory": {"pid": _ws_pid}})

# ------------------------------------------------------------- avatars ----

func spawn_remote_avatars() -> void:
	for pid in multiplayer.get_peers():
		_ensure_avatar(pid)

func _ensure_avatar(pid: int) -> void:
	if not online or _avatars.has(pid) or world == null:
		return
	const RemoteAvatarScript := preload("res://game/scripts/remote_avatar.gd")
	var av: Node3D = RemoteAvatarScript.new()
	av.name = "RemotePlayer_%d" % pid
	av.peer_id = pid
	world.add_child(av)
	av.set_name_tag("PLAYER %d" % pid)
	_avatars[pid] = av

func _remove_avatar(pid: int) -> void:
	if _avatars.has(pid):
		_avatars[pid].queue_free()
		_avatars.erase(pid)

func _clear_avatars() -> void:
	for pid in _avatars.keys():
		_remove_avatar(pid)

func remote_position(pid: int) -> Vector3:
	if _avatars.has(pid):
		return _avatars[pid].global_position
	return Vector3.INF

func nearest_remote_to(pos: Vector3, max_dist := INF) -> Dictionary:
	## {"peer_id": int, "pos": Vector3} of the closest remote player, or {}
	var best := {}
	var best_d := max_dist
	for pid in _avatars.keys():
		var d: float = pos.distance_to(_avatars[pid].global_position)
		if d < best_d:
			best_d = d
			best = {"peer_id": pid, "pos": _avatars[pid].global_position}
	return best

# ------------------------------------------------------- loot claiming ----

func claim_box(pos: Vector3) -> void:
	## First taker wins: the collector's peer frees the box everywhere.
	if not online:
		return
	if _ws_mode:
		# the server relays RemoveBox back to everyone (incl. the taker)
		send_box_taken(pos)
		return
	if is_host():
		_box_taken_local(pos)
		rpc("rpc_remove_box", pos)
	else:
		rpc("rpc_box_taken", pos)

func _box_taken_local(pos: Vector3) -> void:
	if world == null:
		return
	var best: Node3D = null
	var best_d := 1.5
	for box in world.get_tree().get_nodes_in_group("loot"):
		var d: float = pos.distance_to(box.global_position)
		if d < best_d:
			best_d = d
			best = box
	if best != null:
		best.queue_free()

# =============================================================== RPCs =====

@rpc("authority", "call_remote", "reliable")
func rpc_seed(seed_value: int, elapsed: float) -> void:
	## Host -> peers: the seed of the world that is/becomes live.
	pending_seed = seed_value
	pending_elapsed = elapsed
	var need_rebuild := world != null and raid_seed != seed_value
	raid_seed = seed_value
	seed_received.emit()
	if need_rebuild:
		world.get_tree().reload_current_scene()

@rpc("authority", "call_remote", "reliable")
func rpc_raid_started() -> void:
	raid_active = true
	raid_started_net.emit()

@rpc("authority", "call_remote", "reliable")
func rpc_net_state(elapsed: float, frenzy: bool) -> void:
	if world == null or world.get("manager") == null:
		return
	var mgr = world.manager
	mgr.net_sync_clock(elapsed, frenzy)

@rpc("any_peer", "call_remote", "unreliable_ordered")
func rpc_player_state(pid: int, pos: Vector3, body_yaw: float, speed: float, on_floor: bool, crouch: bool) -> void:
	if not _avatars.has(pid):
		_ensure_avatar(pid)
	if _avatars.has(pid):
		_avatars[pid].set_state(pos, body_yaw, speed, on_floor, crouch)

@rpc("authority", "call_remote", "unreliable_ordered")
func rpc_zombie_states(arr: PackedFloat32Array) -> void:
	if world == null or world.get("manager") == null or arr.size() < 1:
		return
	var mgr = world.manager
	var seq := int(arr[0])
	var i := 1
	while i + 6 < arr.size():
		var id := int(arr[i])
		var pos := Vector3(arr[i + 1], arr[i + 2], arr[i + 3])
		var z := _zombie_by_id(id)
		if z == null:
			# First sighting of this zombie on this client: mirror it.
			# (MC: unknown entity in an update packet is silently ignored —
			# we go one better and lazily instantiate the mirror.)
			mgr.net_spawn_mirror(id, pos, int(arr[i + 6]))
			z = _zombie_by_id(id)
		if z != null:
			z.net_update(pos, arr[i + 4], int(arr[i + 5]), seq)
		i += 7

@rpc("any_peer", "call_remote", "reliable")
func rpc_hit_zombie(net_id: int, dmg: float) -> void:
	## client -> host: a bullet landed on a zombie.
	## The host owns zombie health and validates the report (MC anti-cheat).
	if not hosting or world == null:
		return
	var sender := multiplayer.get_remote_sender_id()
	var now := Time.get_ticks_msec() / 1000.0
	if now - float(_hit_times.get(sender, -99.0)) < 1.0 / MAX_HIT_RATE:
		return  # flooding: reject
	_hit_times[sender] = now
	var z := _zombie_by_id(net_id)
	if z == null:
		return  # unknown entity: ignore silently
	var shooter_pos := remote_position(sender)
	if shooter_pos != Vector3.INF and shooter_pos.distance_to(z.global_position) > MAX_HIT_RANGE:
		return  # impossible shot: ignore
	z.apply_net_damage(clampf(dmg, 0.0, MAX_HIT_DAMAGE))

@rpc("authority", "call_remote", "reliable")
func rpc_zombie_dead(net_id: int, pos: Vector3, drop_value: int) -> void:
	if world == null:
		return
	var z := _zombie_by_id(net_id)
	if z != null:
		z.net_die()
	if world.get("manager") != null:
		world.manager.net_on_zombie_dead(pos, drop_value)

@rpc("any_peer", "call_remote", "reliable")
func rpc_box_taken(pos: Vector3) -> void:
	## client -> host: I took this box; host frees it and relays to everyone
	if hosting:
		_box_taken_local(pos)
		rpc("rpc_remove_box", pos)

@rpc("authority", "call_remote", "reliable")
func rpc_remove_box(pos: Vector3) -> void:
	_box_taken_local(pos)

@rpc("any_peer", "call_remote", "reliable")
func rpc_report_extract(_in_zone: bool) -> void:
	## client -> host: a client finished the extraction timer
	if hosting and world != null and world.get("manager") != null:
		world.manager.net_extract_report()

@rpc("authority", "call_remote", "reliable")
func rpc_extract_success() -> void:
	raid_active = false
	extract_success_net.emit()

@rpc("any_peer", "call_remote", "reliable")
func rpc_report_player_died() -> void:
	## client -> host: I died — the whole team loses the raid
	if hosting:
		rpc("rpc_raid_failed")
		raid_failed_net.emit()

@rpc("authority", "call_remote", "reliable")
func rpc_raid_failed() -> void:
	raid_active = false
	raid_failed_net.emit()

@rpc("authority", "call_remote", "reliable")
func rpc_damage_player(dmg: float) -> void:
	## host -> one client: a zombie hit YOUR body
	if world != null and world.get("player") != null:
		world.player.get_damage(dmg)

func _zombie_by_id(zid: int) -> Node:
	if world == null:
		return null
	return world.get_node_or_null(NodePath("Z_%d" % zid))
