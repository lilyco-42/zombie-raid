extends SceneTree
## Headless verification: Minecraft-style C/S net core.
## Run: godot --headless --path . --script tests/test_net.gd
## Covers: seed handshake, lazy zombie mirroring (+dedup), box claim
## resolution, host-side hit validation (rate / damage / range).

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

func _make_script(source: String) -> GDScript:
	var gs := GDScript.new()
	gs.source_code = source
	gs.reload()
	return gs

const ZSTUB_SRC := """
extends CharacterBody3D
var net_id := 0
var ztype := 0
var state := 1
var last_pos := Vector3.ZERO
var last_seq := -1
var damage_taken: Array = []
func is_dead() -> bool:
	return false
func apply_net_damage(d: float) -> void:
	damage_taken.append(d)
func net_update(pos: Vector3, yaw: float, code: int, seq: int) -> void:
	last_pos = pos
	last_seq = seq
"""

const MGRSTUB_SRC := """
extends Node
var _frenzy := false
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
"""

const WORLDSTUB_SRC := """
extends Node3D
var manager = null
"""

func _run() -> void:
	var net = root.get_node("Net")
	var zstub := _make_script(ZSTUB_SRC)

	# --- A. seed handshake (world not yet built) -------------------------
	var seeds_seen: Array = []
	net.seed_received.connect(func(): seeds_seen.append(1))
	net.rpc_seed(777, 12.5)
	_check("seed stored", int(net.pending_seed) == 777 and int(net.raid_seed) == 777)
	_check("seed elapsed stored", absf(float(net.pending_elapsed) - 12.5) < 0.01)
	_check("seed_received emitted", seeds_seen.size() == 1)

	# --- B. snapshot -> lazy mirror (+dedup) ------------------------------
	var world: Node3D = _make_script(WORLDSTUB_SRC).new()
	root.add_child(world)
	net.world = world
	var mgr = _make_script(MGRSTUB_SRC).new()
	mgr.stub = zstub
	world.add_child(mgr)
	world.manager = mgr

	var snap := PackedFloat32Array([100.0, 42.0, 1.0, 2.0, 3.0, 0.5, 2.0, 3.0])
	net.rpc_zombie_states(snap)
	_check("mirror requested once", mgr.mirrored.size() == 1 and int(mgr.mirrored[0][0]) == 42)
	_check("mirror type passed", int(mgr.mirrored[0][2]) == 3)
	var z = world.get_node_or_null(NodePath("Z_42"))
	_check("mirror node created", z != null)
	_check("mirror got first update", z != null and int(z.last_seq) == 100)

	# Second snapshot: same id, new position — must dedup and update
	var snap2 := PackedFloat32Array([102.0, 42.0, 9.0, 9.0, 9.0, 0.5, 4.0, 3.0])
	net.rpc_zombie_states(snap2)
	_check("mirror deduped", mgr.mirrored.size() == 1)
	_check("mirror updated", z != null and z.last_pos == Vector3(9, 9, 9) and int(z.last_seq) == 102)

	# --- C. box claim resolution (nearest loot wins) ----------------------
	var loot_script: GDScript = load("res://game/scripts/loot_box.gd")
	var box_a := Area3D.new()
	box_a.set_script(loot_script)
	world.add_child(box_a)
	box_a.global_position = Vector3.ZERO
	var box_b := Area3D.new()
	box_b.set_script(loot_script)
	world.add_child(box_b)
	box_b.global_position = Vector3(5, 0, 0)
	net._box_taken_local(Vector3(0.3, 0, 0))
	_check("nearest box freed", box_a.is_queued_for_deletion() and not box_b.is_queued_for_deletion())
	net._box_taken_local(Vector3(4.9, 0, 0))
	_check("second box freed", box_b.is_queued_for_deletion())

	# --- D. hit validation (MC-style server authority) --------------------
	var z9: CharacterBody3D = zstub.new()
	z9.net_id = 9
	z9.name = "Z_9"
	world.add_child(z9)
	z9.add_to_group("zombie")
	net.online = true
	net.hosting = true

	net.rpc_hit_zombie(9, 500.0)
	_check("damage clamped", z9.damage_taken == [80.0])
	net.rpc_hit_zombie(9, 10.0)
	_check("rate limited", z9.damage_taken.size() == 1)

	# simulate an old last-hit so the rate limiter lets the next through
	net._hit_times[0] = Time.get_ticks_msec() / 1000.0 - 1.0
	var far := Node3D.new()
	world.add_child(far)
	far.global_position = Vector3(500, 0, 0)
	net._avatars[0] = far  # shooter 500m away
	net.rpc_hit_zombie(9, 10.0)
	_check("range rejected", z9.damage_taken.size() == 1)
	# the rejected report consumed the rate budget too (strict anti-flood):
	# simulate the 50ms cooldown before the next legitimate shot
	net._hit_times[0] = Time.get_ticks_msec() / 1000.0 - 1.0
	far.global_position = Vector3(2, 0, 0)
	net.rpc_hit_zombie(9, 10.0)
	_check("valid hit applied", z9.damage_taken == [80.0, 10.0])

	print("net test done: %s" % ("ALL PASS" if fails == 0 else "%d FAILED" % fails))
	quit(1 if fails > 0 else 0)
