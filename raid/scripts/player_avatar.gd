extends Node3D
## Third-person avatar: KayKit Rogue_Hooded body + over-the-shoulder camera.
## V toggles FP/TP. In TP we mirror the (hidden) FP camera's yaw/pitch onto
## the rig, so lean/crouch/sprint from the template all keep working, and the
## body plays KayKit locomotion animations driven by the player's velocity.

const MODEL := "res://assets/kaykit/adventurers/Rogue_Hooded.glb"
const BODY_HEIGHT := 1.8

const PIVOT_HEIGHT := 1.55
const PIVOT_HEIGHT_CROUCH := 1.0
const SHOULDER_OFFSET := Vector3(0.55, 0.1, 0)
const ARM_LENGTH := 3.2

var fp_mode := true

var player: CharacterBody3D
var fp_camera: Camera3D
var tp_camera: Camera3D
var weapons_models: Node3D
var body_pivot: Node3D
var body_anim: AnimationPlayer
var arm: SpringArm3D
var pivot: Node3D
var torch: SpotLight3D

func _ready() -> void:
	player = get_parent()
	_find_fp_camera()
	_build_body()
	_build_tp_rig()
	_build_flashlight()
	_apply_mode()

func _build_flashlight() -> void:
	# Head torch on the FP camera: works in both view modes, follows the aim
	if fp_camera == null:
		return
	torch = SpotLight3D.new()
	torch.light_color = Color(1.0, 0.93, 0.8)
	torch.light_energy = 2.6
	torch.spot_range = 20.0
	torch.spot_angle = 27.0
	torch.spot_angle_attenuation = 0.8
	torch.shadow_enabled = true
	torch.position = Vector3(0.15, -0.12, 0)
	fp_camera.add_child(torch)

func _find_fp_camera() -> void:
	for cam in player.find_children("*", "Camera3D", true, false):
		if cam.name == "MainCamera" or cam.name.begins_with("MainCamera"):
			fp_camera = cam
			break
	if fp_camera == null:
		var cams := player.find_children("*", "Camera3D", true, false)
		fp_camera = cams[0] if not cams.is_empty() else null
	weapons_models = player.find_child("Weapons_Models", true, false) as Node3D

func _build_body() -> void:
	body_pivot = Node3D.new()
	body_pivot.name = "BodyPivot"
	add_child(body_pivot)
	if ResourceLoader.exists(MODEL):
		var model: Node3D = (load(MODEL) as PackedScene).instantiate()
		body_pivot.add_child(model)
		var box := _aabb_of(model)
		if box.size.y > 0.05:
			model.scale = Vector3.ONE * (BODY_HEIGHT / box.size.y)
		body_anim = model.get_node_or_null("AnimationPlayer")
		if body_anim:
			for looped in ["Idle", "Walking_A", "Running_A", "Jump_Idle", "2H_Melee_Idle"]:
				var a := body_anim.get_animation(looped)
				if a:
					a.loop_mode = Animation.LOOP_LINEAR

func _build_tp_rig() -> void:
	pivot = Node3D.new()
	pivot.name = "TPPivot"
	pivot.position = Vector3(0, PIVOT_HEIGHT, 0)
	add_child(pivot)
	arm = SpringArm3D.new()
	arm.spring_length = ARM_LENGTH
	arm.margin = 0.25
	arm.collision_mask = 1  # world only; never clip against the player
	arm.position = SHOULDER_OFFSET
	pivot.add_child(arm)
	tp_camera = Camera3D.new()
	tp_camera.fov = 75.0
	arm.add_child(tp_camera)

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("toggle_view"):
		fp_mode = not fp_mode
		_apply_mode()
	if event.is_action_pressed("flashlight") and torch:
		torch.visible = not torch.visible
		Sfx.reload_click(player.global_position)

func _apply_mode() -> void:
	body_pivot.visible = not fp_mode
	if weapons_models:
		weapons_models.visible = fp_mode
	if fp_mode:
		if fp_camera:
			fp_camera.current = true
	else:
		tp_camera.current = true

func _physics_process(_delta: float) -> void:
	if fp_camera == null:
		return
	var fwd := -fp_camera.global_transform.basis.z
	var yaw := atan2(-fwd.x, -fwd.z)
	var pitch := asin(clampf(fwd.y, -1.0, 1.0))

	if not fp_mode:
		pivot.global_rotation = Vector3(0.0, yaw, 0.0)
		arm.rotation.x = clampf(pitch, deg_to_rad(-60), deg_to_rad(60))
		# crouch lowers the shoulder
		var target_h := PIVOT_HEIGHT_CROUCH if player.get("crouched") else PIVOT_HEIGHT
		pivot.position.y = lerpf(pivot.position.y, target_h, minf(10.0 * _delta, 1.0))
		_animate_body(fwd, yaw, _delta)

func _animate_body(fwd: Vector3, _yaw: float, delta: float) -> void:
	if body_pivot == null or body_anim == null:
		return
	# Face the camera direction (strafe-style aiming), fallback to velocity
	var face := Vector3(fwd.x, 0, fwd.z)
	if face.length_squared() < 0.01:
		var v := player.velocity
		face = Vector3(v.x, 0, v.z)
	if face.length_squared() > 0.01:
		var target_yaw := atan2(face.x, face.z)  # KayKit models face +Z
		body_pivot.rotation.y = lerp_angle(body_pivot.rotation.y, target_yaw, minf(12.0 * delta, 1.0))

	var speed := Vector3(player.velocity.x, 0, player.velocity.z).length()
	var next := "Idle"
	if not player.is_on_floor():
		next = "Jump_Idle"
	elif speed > 4.5:
		next = "Running_A"
	elif speed > 0.5:
		next = "Walking_A"
	if body_anim.current_animation != next and body_anim.has_animation(next):
		body_anim.play(next)

func _aabb_of(inst: Node3D) -> AABB:
	var total := AABB()
	var has := false
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		var rel: Transform3D = inst.global_transform.affine_inverse() * mi.global_transform
		var box: AABB = rel * mi.get_aabb()
		total = box if not has else total.merge(box)
		has = true
	return total
