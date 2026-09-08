extends Node3D
## RemoteAvatar — lightweight stand-in for another player's body.
## No camera, no input, no physics: position/yaw/animation are fed by Net
## at 15 Hz and interpolated here. Carries a name tag so you can tell
## the squad apart in the dark.

const MODEL := "res://assets/kaykit/adventurers/Rogue_Hooded.glb"
const BODY_HEIGHT := 1.8
const INTERP := 12.0

var peer_id := 1             # owning ENet peer (set by Net._ensure_avatar)
var body_pivot: Node3D
var anim: AnimationPlayer
var tag: Label3D

var _target_pos := Vector3.ZERO
var _target_yaw := 0.0
var _speed := 0.0
var _crouch := false
var _has_state := false

func _ready() -> void:
	add_to_group("remote_player")
	_build_body()
	_build_tag()

func _build_body() -> void:
	body_pivot = Node3D.new()
	body_pivot.name = "BodyPivot"
	add_child(body_pivot)
	if not ResourceLoader.exists(MODEL):
		return
	var model: Node3D = (load(MODEL) as PackedScene).instantiate()
	body_pivot.add_child(model)
	var box := _aabb_of(model)
	if box.size.y > 0.05:
		model.scale = Vector3.ONE * (BODY_HEIGHT / box.size.y)
	anim = model.get_node_or_null("AnimationPlayer")
	if anim:
		for looped in ["Idle", "Walking_A", "Running_A"]:
			var a := anim.get_animation(looped)
			if a:
				a.loop_mode = Animation.LOOP_LINEAR
		anim.play("Idle")

func _build_tag() -> void:
	tag = Label3D.new()
	tag.text = "PLAYER"
	tag.font_size = 40
	tag.pixel_size = 0.005
	tag.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	tag.modulate = Color(0.6, 0.9, 1.0)
	tag.outline_size = 8
	add_child(tag)
	tag.position.y = BODY_HEIGHT + 0.45

func get_damage(dmg: float) -> void:
	## Zombies on the host can hit remote players: relay to the owning client.
	Net.rpc_id(peer_id, "rpc_damage_player", dmg)

func set_name_tag(player_name: String) -> void:
	if tag:
		tag.text = player_name

func set_state(pos: Vector3, body_yaw: float, speed: float, on_floor: bool, crouch: bool) -> void:
	if not _has_state:
		_has_state = true
		global_position = pos  # snap on first packet
	_target_pos = pos
	_target_yaw = body_yaw
	_speed = speed
	_crouch = crouch

func _physics_process(delta: float) -> void:
	if not _has_state:
		return
	var k := minf(INTERP * delta, 1.0)
	global_position = global_position.lerp(_target_pos, k)
	body_pivot.rotation.y = lerp_angle(body_pivot.rotation.y, _target_yaw, k)
	if anim:
		var next := "Idle"
		if _speed > 4.5:
			next = "Running_A"
		elif _speed > 0.5:
			next = "Walking_A"
		if anim.current_animation != next and anim.has_animation(next):
			anim.play(next)
		anim.speed_scale = clampf(_speed / 2.0, 0.7, 1.6)

func _aabb_of(inst: Node3D) -> AABB:
	var total := AABB()
	var has := false
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		var rel: Transform3D = inst.global_transform.affine_inverse() * mi.global_transform
		var box: AABB = rel * mi.get_aabb()
		total = box if not has else total.merge(box)
		has = true
	return total
