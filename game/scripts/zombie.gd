extends CharacterBody3D
## Zombie enemy. Wanders the city, chases the player on sight,
## melees in range, plays KayKit skeleton animations.
## Damage intake is wired to the FPS template's projectile system:
## we are in the "Target" group and expose Hit_Successful().

enum State { SPAWNING, WANDER, CHASE, ATTACK, DEAD }

const AGGRO_RANGE := 20.0
const DEAGGRO_RANGE := 34.0
const ATTACK_RANGE := 2.0
const ATTACK_COOLDOWN := 1.3
const ATTACK_HIT_DELAY := 0.4
const WANDER_RADIUS := 9.0

@export var max_health: float = 60.0
@export var model_path: String = ""          # empty = keep the scene's default Minion model
@export var body_height := 1.7
@export var walk_speed := 1.7
@export var run_speed := 4.0
@export var attack_damage := 15.0
@export var tint := Color(0.62, 1.0, 0.62)   # undead skin tint

signal died(at_position: Vector3)

var state: int = State.SPAWNING
var health: float
var home_position: Vector3
var net_id := 0                # >0 once the host registers this zombie online
var ztype := 0                 # 0..2 = VARIANTS index, 3 = spitter (mirrored on clients)
var _has_net := false
var _net_buf: Array = []       # snapshot ring: {seq, pos, yaw, code} (MC-style)
var _wander_timer := 0.0
var _attack_timer := 0.0
var _growl_timer := 0.0
var _fallback_dir := Vector3.ZERO
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

@onready var nav_agent: NavigationAgent3D = $NavAgent
@onready var model: Node3D = $Model

var anim: AnimationPlayer

func _ready() -> void:
	add_to_group("zombie")
	health = max_health
	home_position = global_position
	_apply_model()
	anim = model.get_node_or_null("AnimationPlayer")
	_normalize_model_scale()
	_tint_model_undead()
	if anim:
		for looped in ["Idle", "Walking_A", "Running_A", "2H_Melee_Idle"]:
			var a := anim.get_animation(looped)
			if a:
				a.loop_mode = Animation.LOOP_LINEAR
		anim.animation_finished.connect(_on_animation_finished)
	_enter_spawn()

func is_dead() -> bool:
	return state == State.DEAD

func _physics_process(delta: float) -> void:
	if state == State.DEAD:
		return
	if Net.online and not Net.is_host():
		_net_physics(delta)
		return
	_attack_timer = maxf(_attack_timer - delta, 0.0)
	_growl_timer -= delta
	if _growl_timer <= 0.0:
		_growl_timer = randf_range(5.0, 11.0)
		if state == State.WANDER or state == State.CHASE:
			Sfx.growl(global_position)

	if not is_on_floor():
		velocity.y -= _gravity * delta

	if state == State.SPAWNING:
		velocity.x = 0
		velocity.z = 0
		move_and_slide()
		return

	var player := _find_player()
	var dist_to_player := INF
	if player:
		dist_to_player = global_position.distance_to(player.global_position)

	# State transitions (simple distance-based senses)
	if state == State.WANDER and dist_to_player < AGGRO_RANGE:
		state = State.CHASE
	elif state == State.CHASE and dist_to_player > DEAGGRO_RANGE:
		state = State.WANDER
		_wander_timer = 0.0

	match state:
		State.WANDER:
			_do_wander(delta)
		State.CHASE:
			if dist_to_player <= ATTACK_RANGE:
				_do_attack(player)
			else:
				_do_chase(player, delta)
		State.ATTACK:
			velocity.x = 0
			velocity.z = 0
			if _attack_timer <= 0.0:
				state = State.CHASE
			elif player and dist_to_player > DEAGGRO_RANGE:
				state = State.CHASE
	move_and_slide()

func _nav_ready() -> bool:
	# WASM safety net: if the navmesh never baked, walk directly instead of freezing
	return NavigationServer3D.map_get_iteration_id(get_world_3d().navigation_map) > 0

func _do_wander(delta: float) -> void:
	if not _nav_ready():
		_wander_timer -= delta
		if _wander_timer <= 0.0:
			_wander_timer = randf_range(2.0, 4.0)
			_fallback_dir = Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)).normalized()
		_play_move_anim(walk_speed, "Walking_A")
		velocity.x = _fallback_dir.x * walk_speed
		velocity.z = _fallback_dir.z * walk_speed
		_face_dir(_fallback_dir, delta)
		return
	_wander_timer -= delta
	if _wander_timer <= 0.0 or nav_agent.is_navigation_finished():
		_wander_timer = randf_range(3.0, 6.0)
		var offset := Vector3(randf_range(-1, 1), 0, randf_range(-1, 1)).normalized() * randf_range(2.0, WANDER_RADIUS)
		nav_agent.target_position = home_position + offset
	_play_move_anim(walk_speed, "Walking_A")
	var dir := _steer_dir()
	velocity.x = dir.x * walk_speed
	velocity.z = dir.z * walk_speed
	_face_dir(dir, delta)

func _do_chase(player: Node3D, delta: float) -> void:
	if not _nav_ready():
		var direct := player.global_position - global_position
		direct.y = 0
		direct = direct.normalized()
		_play_move_anim(run_speed, "Running_A")
		velocity.x = direct.x * run_speed
		velocity.z = direct.z * run_speed
		_face_dir(direct, delta)
		return
	nav_agent.target_position = player.global_position
	_play_move_anim(run_speed, "Running_A")
	var dir := _steer_dir()
	velocity.x = dir.x * run_speed
	velocity.z = dir.z * run_speed
	_face_dir(dir, delta)

func _do_attack(player: Node3D) -> void:
	if _attack_timer > 0.0:
		return
	_attack_timer = ATTACK_COOLDOWN
	state = State.ATTACK
	velocity.x = 0
	velocity.z = 0
	_face_position(player.global_position)
	Sfx.screech(global_position)
	if anim and anim.has_animation("Unarmed_Melee_Attack_Punch_A"):
		anim.play("Unarmed_Melee_Attack_Punch_A")
	# Damage lands mid-swing only if the player is still in range
	get_tree().create_timer(ATTACK_HIT_DELAY).timeout.connect(func():
		if state == State.DEAD:
			return
		var p := _find_player()
		if p and p.has_method("get_damage") and global_position.distance_to(p.global_position) <= ATTACK_RANGE + 0.6:
			p.get_damage(attack_damage)
	)

func _steer_dir() -> Vector3:
	# Web fallback: if the navmesh never baked, steer straight at the target
	# instead of standing still (walls be damned - moving beats statues).
	if NavigationServer3D.map_get_iteration_id(get_world_3d().navigation_map) == 0:
		var direct := nav_agent.target_position - global_position
		direct.y = 0
		return direct.normalized() if direct.length_squared() > 0.01 else Vector3.ZERO
	if nav_agent.is_navigation_finished():
		return Vector3.ZERO
	var next := nav_agent.get_next_path_position()
	var dir := next - global_position
	dir.y = 0
	if dir.length_squared() < 0.001:
		# Pathless agent (e.g. unreachable target): head straight for the target
		var fallback := nav_agent.target_position - global_position
		fallback.y = 0
		return fallback.normalized() if fallback.length_squared() > 0.01 else Vector3.ZERO
	return dir.normalized()

func _face_dir(dir: Vector3, delta: float) -> void:
	if dir.length_squared() < 0.001:
		return
	var target_yaw := atan2(dir.x, dir.z)
	model.rotation.y = lerp_angle(model.rotation.y, target_yaw, minf(10.0 * delta, 1.0))

func _face_position(pos: Vector3) -> void:
	var dir := pos - global_position
	dir.y = 0
	if dir.length_squared() > 0.001:
		model.rotation.y = atan2(dir.x, dir.z)

func _play_move_anim(speed: float, move_anim: String) -> void:
	if not anim:
		return
	if state == State.ATTACK:
		return
	var current := anim.current_animation
	if current == move_anim:
		return
	if anim.has_animation(move_anim):
		anim.play(move_anim)
		anim.speed_scale = clampf(speed / 2.0, 0.7, 1.8)

func _on_animation_finished(anim_name: StringName) -> void:
	match String(anim_name):
		"Unarmed_Melee_Attack_Punch_A":
			if state == State.ATTACK and _attack_timer > 0.0:
				if anim and anim.has_animation("2H_Melee_Idle"):
					anim.play("2H_Melee_Idle")
		"Spawn_Ground":
			state = State.WANDER
			_wander_timer = 0.0
		"Death_A", "Death_B":
			var t := get_tree().create_timer(6.0)
			t.timeout.connect(queue_free)

func _enter_spawn() -> void:
	# Network mirrors skip the crawl-out intro: they are spawned mid-raid
	if _has_net:
		state = State.WANDER
		_wander_timer = 0.0
		return
	# Rise from the ground: zombie crawl-out intro, invulnerable-ish while spawning
	nav_agent.target_position = home_position
	if anim and anim.has_animation("Spawn_Ground"):
		anim.play("Spawn_Ground")
		state = State.SPAWNING
	else:
		state = State.WANDER

func _find_player() -> Node3D:
	## Host: nearest of (local player, remote avatars) — zombies threaten everyone.
	## Client/offline: the local player.
	var local := get_tree().get_first_node_in_group("player") as Node3D
	if not (Net.online and Net.is_host()):
		return local
	var best := local
	var best_d := INF
	if local != null:
		best_d = global_position.distance_to(local.global_position)
	for r in get_tree().get_nodes_in_group("remote_player"):
		var d: float = global_position.distance_to(r.global_position)
		if d < best_d:
			best_d = d
			best = r
	return best

# --- Network mirror (clients only) ---
const NET_BUFFER := 8          # interpolation buffer depth (snapshots)
const NET_DELAY := 3.0         # render N snapshots behind the host (MC lerpSteps=3)

func net_update(pos: Vector3, yaw: float, code: int, seq: int) -> void:
	## Host snapshot (15 Hz, sequence-numbered) -> interpolation buffer.
	## Like MC: the client never runs zombie AI, it replays buffered states.
	_has_net = true
	if _net_buf.is_empty():
		global_position = pos  # first sighting: snap
	_net_buf.append({"seq": seq, "pos": pos, "yaw": yaw, "code": code})
	while _net_buf.size() > NET_BUFFER:
		_net_buf.pop_front()

func _net_physics(_delta: float) -> void:
	## MC entity interpolation: play the buffer INTERP_SNAPSHOTS samples in
	## the past, lerping between the two snapshots that straddle the playhead.
	if not _has_net or _net_buf.is_empty():
		return
	var target := float(_net_buf[_net_buf.size() - 1]["seq"]) - NET_DELAY
	var s0: Dictionary = _net_buf[0]
	var s1: Dictionary = s0
	for i in _net_buf.size():
		if float(_net_buf[i]["seq"]) <= target:
			s0 = _net_buf[i]
			s1 = _net_buf[i + 1] if i + 1 < _net_buf.size() else _net_buf[i]
	var alpha := 0.0
	if float(s1["seq"]) > float(s0["seq"]):
		alpha = clampf((target - float(s0["seq"])) / (float(s1["seq"]) - float(s0["seq"])), 0.0, 1.0)
	var pos: Vector3 = s0["pos"].lerp(s1["pos"], alpha)
	if global_position.distance_to(pos) > 10.0:
		global_position = pos  # teleport / long stall: snap
	else:
		global_position = pos
	model.rotation.y = lerp_angle(s0["yaw"], s1["yaw"], alpha)
	if anim:
		match int(s1["code"]):
			4:
				_net_play("Unarmed_Melee_Attack_Punch_A", 1.0)
			2:
				_net_play("Running_A", clampf(run_speed / 2.0, 0.7, 1.8))
			_:
				_net_play("Idle", 1.0)

func _net_play(anim_name: String, speed: float) -> void:
	if anim.current_animation != anim_name and anim.has_animation(anim_name):
		anim.play(anim_name)
		anim.speed_scale = speed

func apply_net_damage(dmg: float) -> void:
	## Host: damage reported by a client's bullet
	if state == State.DEAD:
		return
	health -= dmg
	if health <= 0.0:
		_die()

func net_die() -> void:
	## Client: the host reports this zombie died — play the death, drop nothing
	## (loot arrives via the manager's net path)
	if state == State.DEAD:
		return
	state = State.DEAD
	remove_from_group("Target")
	collision_layer = 0
	collision_mask = 0
	Sfx.zombie_death(global_position)
	if anim:
		anim.speed_scale = 1.0
		anim.play("Death_A" if anim.has_animation("Death_A") else "T-Pose")

# --- Template projectile interface ---
func Hit_Successful(damage: float, _Direction: Vector3 = Vector3.ZERO, _Position: Vector3 = Vector3.ZERO) -> void:
	if state == State.DEAD:
		return
	if Net.online and not Net.is_host():
		# Client: the host owns zombie health — report the hit, play feedback
		if net_id > 0:
			Net.rpc("rpc_hit_zombie", net_id, damage)
			Sfx.flesh_hit(global_position)
		return
	health -= damage
	Sfx.flesh_hit(global_position)
	if health <= 0.0:
		_die()
	elif anim and anim.has_animation("Hit_A"):
		anim.play("Hit_A")
		if state == State.CHASE or state == State.WANDER:
			# Getting shot interrupts: brief hit pause then resume chase on player
			_attack_timer = maxf(_attack_timer, 0.35)

func _die() -> void:
	state = State.DEAD
	remove_from_group("Target")
	collision_layer = 0
	collision_mask = 0
	velocity = Vector3.ZERO
	Sfx.zombie_death(global_position)
	if anim:
		anim.speed_scale = 1.0
		anim.play("Death_A" if anim.has_animation("Death_A") else "T-Pose")
	died.emit(global_position)

# --- Model helpers ---
func _apply_model() -> void:
	# Variants swap the skeleton model at spawn time (Rogue/Minion/Warrior GLBs)
	if model_path.is_empty():
		return
	var scene: PackedScene = load(model_path)
	if scene == null:
		return
	for child in model.get_children():
		child.queue_free()
	var inst: Node3D = scene.instantiate()
	model.add_child(inst)

func _normalize_model_scale() -> void:
	var box := _model_aabb()
	if box.size.y > 0.05:
		model.scale = Vector3.ONE * (body_height / box.size.y)

func _model_aabb() -> AABB:
	var total := AABB()
	var has := false
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		var rel: Transform3D = model.global_transform.affine_inverse() * mi.global_transform
		var box: AABB = rel * mi.get_aabb()
		total = box if not has else total.merge(box)
		has = true
	return total

func _tint_model_undead() -> void:
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		for i in mi.get_surface_override_material_count():
			var mesh: Mesh = mi.mesh
			if mesh == null:
				continue
			var src: Material = mesh.surface_get_material(i)
			if src == null:
				continue
			var tinted: Material = src.duplicate()
			if tinted is BaseMaterial3D:
				tinted.albedo_color = tint
			mi.set_surface_override_material(i, tinted)


func frenzy() -> void:
	## Moon-departure frenzy: faster, relentless, already knows where you are
	if state == State.DEAD:
		return
	walk_speed *= 1.5
	run_speed *= 1.6
	health = minf(health + 20.0, max_health * 1.5)
	state = State.CHASE
	if anim:
		anim.speed_scale = 1.15
