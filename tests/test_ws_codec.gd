extends SceneTree
## Headless verification: WS codec between net.gd (_ws_mode) and the Rust
## server's serde externally-tagged JSON (protocol crate is the source of
## truth). Run: godot --headless --path . --script tests/test_ws_codec.gd
## Covers: C2S JSON shapes (anti-drift), S2C dispatch (Seed, snapshot
## rebuild to the ENet float layout, clock, death, raid end), DamagePlayer
## pid filter, disconnect -> leave().

var fails := 0

func _initialize() -> void:
	# --script mode may skip autoloads; provide them manually where needed
	if not root.has_node("Net"):
		var net := Node.new()
		net.name = "Net"
		net.set_script(load("res://game/scripts/net.gd"))
		root.add_child(net)
	_run.call_deferred()

func _check(name: String, ok: bool) -> void:
	print(("PASS " if ok else "FAIL ") + name)
	if not ok:
		fails += 1

## Godot's JSON parser decodes every number as float, while our expected
## literals use ints for id/pid fields — and Dictionary deep-compare is
## strict about int vs float. Normalize both sides (ints -> floats) before
## comparing; the Rust roundtrip tests already pin exact wire typing.
func _norm(v: Variant) -> Variant:
	if v is Dictionary:
		var out := {}
		for k in v:
			out[k] = _norm(v[k])
		return out
	if v is Array:
		var arr: Array = []
		for x in v:
			arr.append(_norm(x))
		return arr
	if v is int:
		return float(v)
	return v

## Parse a captured wire line and compare against the expected serde shape.
## Prints both sides on mismatch so drift is diagnosable from the log.
func _shape_check(name: String, line: String, expected: Dictionary) -> void:
	var m: Variant = JSON.parse_string(line)
	if _norm(m) != _norm(expected):
		print("  sent:   ", line)
		print("  parsed: ", m)
	_check(name, _norm(m) == _norm(expected))

func _make_script(source: String) -> GDScript:
	var gs := GDScript.new()
	gs.source_code = source
	gs.reload()
	return gs

const TRANSPORTSTUB_SRC := """
extends RefCounted
var sent: Array = []
var closed := false
func join(_url: String) -> Error:
	return OK
func close() -> void:
	closed = true
func is_open() -> bool:
	return not closed
func is_closed() -> bool:
	return closed
func send_text(line: String) -> void:
	sent.append(line)
func poll_texts() -> PackedStringArray:
	return PackedStringArray()
"""

## Stub whose poll_texts replays queued raw wire lines (pump-driven tests).
const FEEDSTUB_SRC := """
extends RefCounted
var feed: Array = []
var closed := false
func close() -> void:
	closed = true
func is_open() -> bool:
	return not closed
func is_closed() -> bool:
	return closed
func send_text(_line: String) -> void:
	pass
func poll_texts() -> PackedStringArray:
	var out := PackedStringArray()
	for line in feed:
		out.append(line)
	feed.clear()
	return out
"""

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
var clock: Array = []
var deaths: Array = []
var stub: GDScript
func net_spawn_mirror(id: int, pos: Vector3, type: int) -> void:
	mirrored.append([id, pos, type])
	var zb: CharacterBody3D = CharacterBody3D.new()
	zb.set_script(stub)
	zb.net_id = id
	zb.name = "Z_%d" % id
	get_parent().add_child(zb)
func net_sync_clock(e: float, f: bool) -> void:
	clock.append([e, f])
func net_on_zombie_dead(pos: Vector3, drop: int) -> void:
	deaths.append([pos, drop])
"""

const WORLDSTUB_SRC := """
extends Node3D
var manager = null
var player = null
"""

const PLAYERSTUB_SRC := """
extends Node3D
var damage_taken: Array = []
func get_damage(d: float) -> void:
	damage_taken.append(d)
"""

func _run() -> void:
	var net = root.get_node("Net")
	var t = _make_script(TRANSPORTSTUB_SRC).new()
	net._transport = t
	net._ws_mode = true
	net._ws_pid = 7
	net.online = true
	net.hosting = false

	# --- A. C2S JSON shapes: field names must match the serde externally-
	#     tagged enums in server/protocol (drift guard) --------------------
	net.send_hit_zombie(9, 34.5)
	_shape_check("HitZombie shape", t.sent[0],
		{"HitZombie": {"pid": 7, "net_id": 9, "dmg": 34.5}})
	net.send_box_taken(Vector3(0, 1, 2))
	_shape_check("BoxTaken shape", t.sent[1],
		{"BoxTaken": {"pos": [0.0, 1.0, 2.0]}})
	net.send_extract(true)
	_shape_check("ReportExtract shape", t.sent[2],
		{"ReportExtract": {"in_zone": true}})
	net.send_player_died()
	var unit: Variant = JSON.parse_string(t.sent[3])
	_check("ReportPlayerDied shape", unit is Dictionary and unit.has("ReportPlayerDied"))
	net.push_player_state(Vector3(1.5, 0, -3.25), 0.7, 4.2, true, false)
	_shape_check("PlayerState shape", t.sent[4],
		{"PlayerState": {"pid": 7, "pos": [1.5, 0.0, -3.25], "yaw": 0.7,
		"speed": 4.2, "on_floor": true, "crouch": false}})
	_check("my_id/is_host in ws mode", net.my_id() == 7 and not net.is_host())

	# --- B. snapshot rebuild: serde ents -> ENet float layout -------------
	var arr: PackedFloat32Array = net._ws_zombie_states_arr({"seq": 5, "ents": [
		{"id": 3, "pos": [1.0, 2.0, 3.0], "yaw": 1.57, "anim": 2, "ztype": 1},
		{"id": 4, "pos": [4.0, 5.0, 6.0], "yaw": 0.0, "anim": 4, "ztype": 3},
	]})
	var want := PackedFloat32Array([5.0,
		3.0, 1.0, 2.0, 3.0, 1.57, 2.0, 1.0,
		4.0, 4.0, 5.0, 6.0, 0.0, 4.0, 3.0])
	_check("snapshot rebuild layout", arr == want)

	# --- C. dispatch through the rpc_* bodies ------------------------------
	# Seed FIRST, while world == null: rpc_seed reloads the scene when the
	# world exists with a different seed, and a --script tree has none.
	var seeds_seen: Array = []
	net.seed_received.connect(func(): seeds_seen.append(1))
	net._dispatch_s2c("Seed", {"seed": 42, "elapsed": 3.0})
	_check("Seed dispatch", int(net.pending_seed) == 42
		and absf(float(net.pending_elapsed) - 3.0) < 0.01
		and seeds_seen.size() == 1)

	# now attach the stub world for the world-consuming handlers
	var world: Node3D = _make_script(WORLDSTUB_SRC).new()
	root.add_child(world)
	net.world = world
	var mgr = _make_script(MGRSTUB_SRC).new()
	mgr.stub = _make_script(ZSTUB_SRC)
	world.add_child(mgr)
	world.manager = mgr

	net._dispatch_s2c("ZombieStates", {"seq": 6, "ents": [
		{"id": 42, "pos": [1.0, 2.0, 3.0], "yaw": 0.5, "anim": 2, "ztype": 3}]})
	_check("ws snapshot mirrors zombie", mgr.mirrored.size() == 1
		and int(mgr.mirrored[0][0]) == 42 and int(mgr.mirrored[0][2]) == 3)
	var z = world.get_node_or_null(NodePath("Z_42"))
	_check("mirror got first update", z != null and int(z.last_seq) == 6)
	# second frame: dedup + update through the same path
	net._dispatch_s2c("ZombieStates", {"seq": 7, "ents": [
		{"id": 42, "pos": [9.0, 9.0, 9.0], "yaw": 0.5, "anim": 4, "ztype": 3}]})
	_check("mirror deduped and updated", mgr.mirrored.size() == 1
		and z != null and z.last_pos == Vector3(9, 9, 9) and int(z.last_seq) == 7)

	net._dispatch_s2c("NetState", {"elapsed": 61.0, "frenzy": true})
	_check("NetState dispatch", mgr.clock.size() == 1
		and absf(float(mgr.clock[0][0]) - 61.0) < 0.01 and bool(mgr.clock[0][1]))

	net._dispatch_s2c("ZombieDead", {"net_id": 42, "pos": [1.0, 2.0, 3.0], "drop_value": 55})
	_check("ZombieDead dispatch", z != null and z.died
		and mgr.deaths.size() == 1 and int(mgr.deaths[0][1]) == 55)

	# --- D. DamagePlayer pid filter (broadcast channel) --------------------
	var pstub = _make_script(PLAYERSTUB_SRC).new()
	world.add_child(pstub)
	world.player = pstub
	net._dispatch_s2c("DamagePlayer", {"pid": 9, "dmg": 12.0})
	_check("foreign DamagePlayer ignored", pstub.damage_taken.is_empty())
	net._dispatch_s2c("DamagePlayer", {"pid": 7, "dmg": 12.0})
	_check("own DamagePlayer applied", pstub.damage_taken == [12.0])

	# --- E. raid end via the REAL wire forms + disconnect ------------------
	# serde emits unit variants as bare JSON strings: the pump must accept
	# both "RaidFailed" and {"ExtractSuccess":null} shapes.
	var t2 = _make_script(FEEDSTUB_SRC).new()
	net._transport = t2
	var fails_seen: Array = []
	net.raid_failed_net.connect(func(): fails_seen.append(1))
	net.raid_active = true
	t2.feed.append("\"RaidFailed\"")
	net._ws_pump(0.0)
	_check("RaidFailed via wire string", fails_seen.size() == 1 and not net.raid_active)

	var extracts_seen: Array = []
	net.extract_success_net.connect(func(): extracts_seen.append(1))
	net.raid_active = true
	t2.feed.append("{\"ExtractSuccess\":null}")
	net._ws_pump(0.0)
	_check("ExtractSuccess via wire map", extracts_seen.size() == 1 and not net.raid_active)

	t2.closed = true
	net._ws_pump(0.0)
	_check("closed socket -> leave()", not net.online and net._transport == null
		and not net._ws_mode)

	print("ws codec test done: %s" % ("ALL PASS" if fails == 0 else "%d FAILED" % fails))
	quit(1 if fails > 0 else 0)
