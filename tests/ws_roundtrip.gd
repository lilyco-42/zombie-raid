extends SceneTree
## End-to-end: real Godot client (net.gd _ws_mode) <-> Rust zraid-server.
## Spawns the server binary, joins over WS, and verifies the whole stack:
## GDScript JSON -> WebSocket -> serde -> World authority -> broadcast ->
## GDScript dispatch -> signals.
## Run: godot --headless --path . --script tests/ws_roundtrip.gd
## Requires: server/target/debug/zraid-server.exe (cargo build in server/).

var fails := 0
var server_pid := -1

func _initialize() -> void:
	_run.call_deferred()

func _check(name: String, ok: bool) -> void:
	print(("PASS " if ok else "FAIL ") + name)
	if not ok:
		fails += 1

func _make_script(source: String) -> GDScript:
	var gs := GDScript.new()
	gs.source_code = source
	gs.reload()
	return gs

const ZSTUB_SRC := """
extends CharacterBody3D
var net_id := 0
var ztype := 0
var last_pos := Vector3.ZERO
var last_seq := -1
var died := false
func is_dead() -> bool:
	return died
func net_update(pos: Vector3, yaw: float, code: int, seq: int) -> void:
	last_pos = pos
	last_seq = seq
func net_die() -> void:
	died = true
"""

const MGRSTUB_SRC := """
extends Node
var mirrored: Array = []
var stub: GDScript
func net_spawn_mirror(id: int, pos: Vector3, type: int) -> void:
	mirrored.append([id, pos, type])
	var zb: CharacterBody3D = CharacterBody3D.new()
	zb.set_script(stub)
	zb.net_id = id
	zb.name = "Z_%d" % id
	get_parent().add_child(zb)
func net_sync_clock(_e: float, _f: bool) -> void:
	pass
func net_on_zombie_dead(_pos: Vector3, _drop: int) -> void:
	pass
"""

const WORLDSTUB_SRC := """
extends Node3D
var manager = null
"""

func _run() -> void:
	var exe := ProjectSettings.globalize_path("res://server/target/debug/zraid-server.exe")
	_check("server binary exists", FileAccess.file_exists(exe))
	if fails > 0:
		quit(1)
		return
	server_pid = OS.create_process(exe, [])
	_check("server spawned", server_pid > 0)
	if server_pid <= 0:
		quit(1)
		return
	await create_timer(1.0).timeout  # give the listener a moment

	if not root.has_node("Net"):
		var net_node := Node.new()
		net_node.name = "Net"
		net_node.set_script(load("res://game/scripts/net.gd"))
		root.add_child(net_node)
	var net = root.get_node("Net")

	var seed_val := {"v": -1}
	net.seed_received.connect(func(): seed_val.v = int(net.raid_seed))
	var failed_flag := {"v": false}
	net.raid_failed_net.connect(func(): failed_flag.v = true)

	_check("join_game(ws://) accepted", net.join_game("ws://127.0.0.1:24565"))
	_check("ws mode on", net._ws_mode and not net.is_host())

	# Seed handshake (server replies immediately on connect)
	var waited := 0.0
	while seed_val.v != 42 and waited < 10.0:
		await create_timer(0.2).timeout
		waited += 0.2
	_check("seed handshake (seed=42)", seed_val.v == 42)

	# attach a stub world AFTER the seed so rpc_seed never triggers a
	# scene reload; snapshots then lazily mirror zombies
	var world: Node3D = _make_script(WORLDSTUB_SRC).new()
	root.add_child(world)
	net.world = world
	var mgr = _make_script(MGRSTUB_SRC).new()
	mgr.stub = _make_script(ZSTUB_SRC)
	world.add_child(mgr)
	world.manager = mgr

	# park the player so the server's spawner has an anchor
	net.push_player_state(Vector3.ZERO, 0.0, 0.0, true, false)

	# server spawns the first zombie ~5s after boot; snapshots every 2 ticks
	waited = 0.0
	while mgr.mirrored.is_empty() and waited < 15.0:
		await create_timer(0.5).timeout
		waited += 0.5
	_check("zombie arrived via snapshot", not mgr.mirrored.is_empty())
	if not mgr.mirrored.is_empty():
		_check("mirror has a real id", int(mgr.mirrored[0][0]) > 0)

	# ---- shop roundtrip (raid active): list + zero-balance rejection -----
	var shop_seen: Array = []
	net.shop_received.connect(func(entries): shop_seen.append(entries))
	net.send_request_shop()
	waited = 0.0
	while shop_seen.is_empty() and waited < 5.0:
		await create_timer(0.2).timeout
		waited += 0.2
	_check("ShopList roundtrip", not shop_seen.is_empty()
		and shop_seen[0].size() >= 2)
	var has_bandage := false
	for e in (shop_seen[0] if not shop_seen.is_empty() else []):
		if e[0] == "bandage":
			has_bandage = true
	_check("shop lists bandage", has_bandage)

	var err_seen: Array = []
	net.trade_error.connect(func(reason): err_seen.append(reason))
	net.send_buy_item("bandage")
	waited = 0.0
	while err_seen.is_empty() and waited < 5.0:
		await create_timer(0.2).timeout
		waited += 0.2
	_check("zero-balance buy rejected", err_seen.size() == 1
		and String(err_seen[0]).contains("insufficient"))

	# a hit report must parse on the server (unknown id -> silently ignored,
	# but the JSON shape has to decode without a "bad message" log line)
	net.send_hit_zombie(9999, 10.0)
	await create_timer(0.3).timeout

	# the full C2S -> World -> S2C roundtrip: my death fails the raid
	net.send_player_died()
	waited = 0.0
	while not failed_flag.v and waited < 5.0:
		await create_timer(0.2).timeout
		waited += 0.2
	_check("RaidFailed roundtrip", failed_flag.v)

	# the same purchase now answers "raid is over" (second TradeError path)
	net.send_buy_item("bandage")
	waited = 0.0
	while err_seen.size() < 2 and waited < 5.0:
		await create_timer(0.2).timeout
		waited += 0.2
	_check("buy after raid over rejected", err_seen.size() == 2
		and String(err_seen[1]).contains("raid is over"))

	# ---- session lifecycle: rejoin starts raid #2 on a fresh seed ---------
	net.leave()
	# back-to-menu: the world goes with the scene, so the reconnect's first
	# Seed (the old raid's tail state) must NOT trigger a scene reload
	net.world = null
	_check("rejoin accepted", net.join_game("ws://127.0.0.1:24565"))
	# once the socket opens the client sends Hello{ver:2}; the server sees
	# the raid is over, resets and broadcasts a brand-new Seed —
	# net.gd's raid_seed must move off 42
	waited = 0.0
	while seed_val.v == 42 and waited < 10.0:
		await create_timer(0.2).timeout
		waited += 0.2
	_check("rejoin starts raid #2 with a fresh seed", seed_val.v != 42)

	# raid #2 actually runs: re-attach the stub world, park, wait for a
	# NEW mirror entry (the old raid's zombie stays in the history array)
	net.world = world
	net.push_player_state(Vector3.ZERO, 0.0, 0.0, true, false)
	var mirrors_before: int = mgr.mirrored.size()
	waited = 0.0
	while mgr.mirrored.size() == mirrors_before and waited < 15.0:
		await create_timer(0.5).timeout
		waited += 0.5
	_check("raid #2 spawns zombies", mgr.mirrored.size() > mirrors_before)

	net.leave()
	OS.kill(server_pid)
	print("ws roundtrip done: %s" % ("ALL PASS" if fails == 0 else "%d FAILED" % fails))
	quit(1 if fails > 0 else 0)
