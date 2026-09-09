extends SceneTree
## Headless verification: WS codec between net.gd (_ws_mode) and the Rust
## server (protocol crate is the source of truth).
## Run: godot --headless --path . --script tests/test_ws_codec.gd
## Covers: C2S JSON shapes (anti-drift), S2C dispatch (Seed, snapshot
## rebuild to the ENet float layout, clock, death, raid end), DamagePlayer
## pid filter, disconnect -> leave(), and section F: the wire format v2
## binary codec (net_codec.gd) against the golden bytes pinned by the
## Rust protocol crate tests.

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

## Records text AND binary sends; poll_frames returns nothing. Used to
## observe what net.gd puts on the wire in both v1 (JSON) and v2 (bincode).
const TRANSPORTSTUB_SRC := """
extends RefCounted
var sent: Array = []
var sent_bytes: Array = []
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
func send_bytes(data: PackedByteArray) -> void:
	sent_bytes.append(data)
func poll_frames() -> Array:
	return []
"""

## Stub whose poll_frames replays queued frames — elements are Strings
## (JSON v1 wire) or PackedByteArrays (bincode v2 wire). Mirrors the real
## transport's dual-format contract.
const FEEDSTUB_SRC := """
extends RefCounted
var feed: Array = []
var sent_bytes: Array = []
var closed := false
func close() -> void:
	closed = true
func is_open() -> bool:
	return not closed
func is_closed() -> bool:
	return closed
func send_text(_line: String) -> void:
	pass
func send_bytes(data: PackedByteArray) -> void:
	sent_bytes.append(data)
func poll_frames() -> Array:
	var out := []
	for f in feed:
		out.append(f)
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

	# --- F. wire format v2: binary codec vs the Rust golden bytes ----------
	# Golden bytes computed with python struct.pack, pinned on the Rust side
	# by server/protocol/src/lib.rs golden_*_tests. Any drift between the
	# GDScript encoder and bincode legacy breaks the live server.
	var NetCodec := load("res://game/scripts/net_codec.gd")

	# F1: decode the golden ZombieStates frame (38 bytes)
	var golden_zs := PackedByteArray([0x01, 0, 0, 0, 0x07, 0, 0, 0,
		0x01, 0, 0, 0, 0, 0, 0, 0,
		0x03, 0, 0, 0,
		0x00, 0x00, 0x80, 0x3f, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x40, 0x40,
		0xc3, 0xf5, 0xc8, 0x3f, 0x02, 0x01])
	var dec: Dictionary = NetCodec.decode_s2c(golden_zs)
	var ok_zs: bool = dec.has("ZombieStates") \
		and int(dec["ZombieStates"]["seq"]) == 7 \
		and dec["ZombieStates"]["ents"].size() == 1
	if ok_zs:
		var e: Dictionary = dec["ZombieStates"]["ents"][0]
		ok_zs = int(e["id"]) == 3 and absf(float(e["yaw"]) - 1.57) < 0.0001 \
			and int(e["anim"]) == 2 and int(e["ztype"]) == 1 \
			and absf(float(e["pos"][0]) - 1.0) < 0.0001 \
			and absf(float(e["pos"][1]) - 2.0) < 0.0001 \
			and absf(float(e["pos"][2]) - 3.0) < 0.0001
	_check("F1 decode golden ZombieStates", ok_zs)

	# F2: decode the golden RaidFailed frame (4 bytes: variant 7 only)
	var dec_rf: Dictionary = NetCodec.decode_s2c(PackedByteArray([0x07, 0, 0, 0]))
	_check("F2 decode golden RaidFailed", dec_rf.size() == 1
		and dec_rf.has("RaidFailed") and dec_rf["RaidFailed"] == null)

	# F3: encode HitZombie -> exact golden bytes
	var golden_hit := PackedByteArray([0x02, 0, 0, 0, 0x02, 0, 0, 0,
		0x09, 0, 0, 0, 0x00, 0x00, 0x0a, 0x42])
	_check("F3 encode golden HitZombie",
		NetCodec.encode_c2s({"HitZombie": {"pid": 2, "net_id": 9, "dmg": 34.5}}) == golden_hit)

	# F4: encode PlayerState -> exact golden bytes (30 bytes)
	var golden_ps := PackedByteArray([0x01, 0, 0, 0, 0x07, 0, 0, 0,
		0x00, 0x00, 0xc0, 0x3f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x50, 0xc0,
		0x33, 0x33, 0x33, 0x3f, 0x66, 0x66, 0x86, 0x40, 0x01, 0x00])
	_check("F4 encode golden PlayerState",
		NetCodec.encode_c2s({"PlayerState": {"pid": 7, "pos": [1.5, 0.0, -3.25],
			"yaw": 0.7, "speed": 4.2, "on_floor": true, "crouch": false}}) == golden_ps)

	# F5: pump over a fresh feed stub -> the binary Hello{ver:2} upgrade
	# frame goes out first, and the negotiation flag flips.
	var t3 = _make_script(FEEDSTUB_SRC).new()
	net._transport = t3
	net._ws_mode = true
	net._ws_pid = 2
	net.online = true
	net._ws_binary = false
	net._ws_hello_sent = false
	var golden_hello := PackedByteArray([0x00, 0, 0, 0, 0x02, 0, 0, 0])
	net._ws_pump(0.0)
	_check("F5 binary Hello upgrade on open", t3.sent_bytes.size() == 1
		and t3.sent_bytes[0] == golden_hello and net._ws_binary)

	# F6: end-to-end binary pump — feed the golden ZombieStates frame as a
	# PackedByteArray and watch it mirror through the SAME dispatch path.
	t3.feed.append(golden_zs)
	net._ws_pump(0.0)
	var z3 = world.get_node_or_null(NodePath("Z_3"))
	_check("F6 binary snapshot mirrors through pump", mgr.mirrored.size() == 2
		and int(mgr.mirrored[1][0]) == 3 and int(mgr.mirrored[1][2]) == 1
		and z3 != null and int(z3.last_seq) == 7)

	# F7: in binary mode the send wrappers emit codec bytes on the wire
	net._ws_pid = 2
	net.send_hit_zombie(9, 34.5)
	_check("F7 send_hit_zombie emits golden bytes", t3.sent_bytes.size() == 2
		and t3.sent_bytes[1] == golden_hit)

	# F8-F12: shop/inventory protocol — same golden bytes as the Rust
	# shop_golden_tests (python struct.pack pinned on both sides)
	# F8: encode RequestShop -> 4 bytes (variant 7 only)
	_check("F8 encode golden RequestShop",
		NetCodec.encode_c2s({"RequestShop": null}) == PackedByteArray([0x07, 0, 0, 0]))

	# F9: encode BuyItem pid=357 "bandage" -> 23 bytes
	var golden_buy := PackedByteArray([0x06, 0, 0, 0, 0x65, 0x01, 0, 0,
		0x07, 0, 0, 0, 0, 0, 0, 0,
		0x62, 0x61, 0x6e, 0x64, 0x61, 0x67, 0x65])
	_check("F9 encode golden BuyItem",
		NetCodec.encode_c2s({"BuyItem": {"pid": 357, "item_id": "bandage"}}) == golden_buy)

	# F10: decode golden TradeError pid=357 "insufficient coins" (34 bytes)
	var golden_err := PackedByteArray([0x0b, 0, 0, 0, 0x65, 0x01, 0, 0,
		0x12, 0, 0, 0, 0, 0, 0, 0,
		0x69, 0x6e, 0x73, 0x75, 0x66, 0x66, 0x69, 0x63, 0x69, 0x65,
		0x6e, 0x74, 0x20, 0x63, 0x6f, 0x69, 0x6e, 0x73])
	var dec_err: Dictionary = NetCodec.decode_s2c(golden_err)
	_check("F10 decode golden TradeError", dec_err.size() == 1
		and dec_err.has("TradeError")
		and int(dec_err["TradeError"]["pid"]) == 357
		and dec_err["TradeError"]["reason"] == "insufficient coins")

	# F11: decode golden InventoryUpdate pid=357 "coin" 1250 (28 bytes)
	var golden_inv := PackedByteArray([0x0a, 0, 0, 0, 0x65, 0x01, 0, 0,
		0x04, 0, 0, 0, 0, 0, 0, 0,
		0x63, 0x6f, 0x69, 0x6e,
		0xe2, 0x04, 0, 0, 0, 0, 0, 0])
	var dec_inv: Dictionary = NetCodec.decode_s2c(golden_inv)
	_check("F11 decode golden InventoryUpdate", dec_inv.size() == 1
		and dec_inv.has("InventoryUpdate")
		and int(dec_inv["InventoryUpdate"]["pid"]) == 357
		and dec_inv["InventoryUpdate"]["item_id"] == "coin"
		and int(dec_inv["InventoryUpdate"]["count"]) == 1250)

	# F12: decode golden ShopList [("bandage",120)] (31 bytes; entries are
	# [id, price] arrays mirroring the JSON tuple shape)
	var golden_shop := PackedByteArray([0x09, 0, 0, 0,
		0x01, 0, 0, 0, 0, 0, 0, 0,
		0x07, 0, 0, 0, 0, 0, 0, 0,
		0x62, 0x61, 0x6e, 0x64, 0x61, 0x67, 0x65,
		0x78, 0, 0, 0])
	var dec_shop: Dictionary = NetCodec.decode_s2c(golden_shop)
	_check("F12 decode golden ShopList", dec_shop.size() == 1
		and dec_shop.has("ShopList")
		and dec_shop["ShopList"]["entries"] == [["bandage", 120]])

	# F13: shop wrappers route through the binary pump like the raid sends
	# (pid must match the golden BuyItem frame)
	var t4 = _make_script(TRANSPORTSTUB_SRC).new()
	net._transport = t4
	net._ws_mode = true
	net._ws_binary = true
	net._ws_pid = 357
	net.send_request_shop()
	net.send_buy_item("bandage")
	_check("F13 shop sends emit codec bytes", t4.sent_bytes.size() == 2
		and t4.sent_bytes[0] == PackedByteArray([0x07, 0, 0, 0])
		and t4.sent_bytes[1] == golden_buy)

	# F14: dispatch of the three shop S2Cs through the real net.gd signals
	var shop_entries: Array = []
	var inv_seen: Array = []
	var err_seen: Array = []
	net.shop_received.connect(func(entries): shop_entries.append(entries))
	net.inventory_update.connect(func(pid, item_id, count): inv_seen.append([pid, item_id, count]))
	net.trade_error.connect(func(reason): err_seen.append(reason))
	net._dispatch_s2c("ShopList", {"entries": [["bandage", 120], ["ammo_box", 250]]})
	net._dispatch_s2c("InventoryUpdate", {"pid": 7, "item_id": "coin", "count": 1250})
	net._dispatch_s2c("TradeError", {"pid": 7, "reason": "insufficient coins"})
	_check("F14 shop dispatches fire signals", shop_entries.size() == 1
		and shop_entries[0] == [["bandage", 120], ["ammo_box", 250]]
		and inv_seen == [[7, "coin", 1250]]
		and err_seen == ["insufficient coins"])

	# G1-G7: account identity — same golden bytes as the Rust auth tests
	# (README_OPS.md T9/T10; docs/CLIENT_API.md §账号)
	# G1: encode Auth pid=357 token "abc12345" -> 24 bytes
	var golden_auth := PackedByteArray([0x08, 0, 0, 0, 0x65, 0x01, 0, 0,
		0x08, 0, 0, 0, 0, 0, 0, 0,
		0x61, 0x62, 0x63, 0x31, 0x32, 0x33, 0x34, 0x35])
	_check("G1 encode golden Auth",
		NetCodec.encode_c2s({"Auth": {"pid": 357, "token": "abc12345"}}) == golden_auth)

	# G2: encode RequestInventory pid=357 -> 8 bytes
	var golden_req_inv := PackedByteArray([0x09, 0, 0, 0, 0x65, 0x01, 0, 0])
	_check("G2 encode golden RequestInventory",
		NetCodec.encode_c2s({"RequestInventory": {"pid": 357}}) == golden_req_inv)

	# G3: decode golden AuthOk uid=1 "survivor#0001" coins=1250 (37 bytes)
	var golden_auth_ok := PackedByteArray([0x0c, 0, 0, 0, 0x01, 0, 0, 0,
		0x0d, 0, 0, 0, 0, 0, 0, 0,
		0x73, 0x75, 0x72, 0x76, 0x69, 0x76, 0x6f, 0x72,
		0x23, 0x30, 0x30, 0x30, 0x31,
		0xe2, 0x04, 0, 0, 0, 0, 0, 0])
	var dec_ao: Dictionary = NetCodec.decode_s2c(golden_auth_ok)
	_check("G3 decode golden AuthOk", dec_ao.size() == 1
		and dec_ao.has("AuthOk")
		and int(dec_ao["AuthOk"]["uid"]) == 1
		and dec_ao["AuthOk"]["name"] == "survivor#0001"
		and int(dec_ao["AuthOk"]["coins"]) == 1250)

	# G4: decode golden AuthErr "invalid token" (25 bytes)
	var golden_auth_err := PackedByteArray([0x0d, 0, 0, 0,
		0x0d, 0, 0, 0, 0, 0, 0, 0,
		0x69, 0x6e, 0x76, 0x61, 0x6c, 0x69, 0x64, 0x20,
		0x74, 0x6f, 0x6b, 0x65, 0x6e])
	var dec_ae: Dictionary = NetCodec.decode_s2c(golden_auth_err)
	_check("G4 decode golden AuthErr", dec_ae.size() == 1
		and dec_ae.has("AuthErr")
		and dec_ae["AuthErr"]["reason"] == "invalid token")

	# G5: decode golden InventorySnapshot [coin 1250, bandage 2] (47 bytes)
	var golden_snap := PackedByteArray([0x0e, 0, 0, 0,
		0x02, 0, 0, 0, 0, 0, 0, 0,
		0x04, 0, 0, 0, 0, 0, 0, 0, 0x63, 0x6f, 0x69, 0x6e,
		0xe2, 0x04, 0, 0, 0, 0, 0, 0,
		0x07, 0, 0, 0, 0, 0, 0, 0, 0x62, 0x61, 0x6e, 0x64,
		0x61, 0x67, 0x65,
		0x02, 0, 0, 0, 0, 0, 0, 0])
	var dec_snap: Dictionary = NetCodec.decode_s2c(golden_snap)
	_check("G5 decode golden InventorySnapshot", dec_snap.size() == 1
		and dec_snap.has("InventorySnapshot")
		and dec_snap["InventorySnapshot"]["entries"] == [["coin", 1250], ["bandage", 2]])

	# G6: account send wrappers route through the binary pump
	var t5 = _make_script(TRANSPORTSTUB_SRC).new()
	net._transport = t5
	net._ws_mode = true
	net._ws_binary = true
	net._ws_pid = 357
	net.send_auth("abc12345")
	net.send_request_inventory()
	_check("G6 account sends emit codec bytes", t5.sent_bytes.size() == 2
		and t5.sent_bytes[0] == golden_auth
		and t5.sent_bytes[1] == golden_req_inv)

	# G7: dispatch of the three account S2Cs through the real net.gd signals
	var auth_oks: Array = []
	var auth_errs: Array = []
	var snapshots: Array = []
	net.auth_ok.connect(func(uid, name, coins): auth_oks.append([uid, name, coins]))
	net.auth_error.connect(func(reason): auth_errs.append(reason))
	net.inventory_snapshot.connect(func(entries): snapshots.append(entries))
	net._dispatch_s2c("AuthOk", {"uid": 1, "name": "survivor#0001", "coins": 1250})
	net._dispatch_s2c("AuthErr", {"reason": "invalid token"})
	net._dispatch_s2c("InventorySnapshot", {"entries": [["coin", 1250], ["bandage", 2]]})
	_check("G7 account dispatches fire signals", auth_oks == [[1, "survivor#0001", 1250]]
		and auth_errs == ["invalid token"]
		and snapshots == [[["coin", 1250], ["bandage", 2]]])

	print("ws codec test done: %s" % ("ALL PASS" if fails == 0 else "%d FAILED" % fails))
	quit(1 if fails > 0 else 0)
