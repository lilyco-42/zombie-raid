extends Area3D
## Teleport portal between the city and the facility interior.
## Cooldown prevents instant ping-pong; visuals are a glowing pad.

signal used(kind: String)

@export var target: Vector3
@export var kind := "enter"  # "enter" (city -> facility) | "exit" (facility -> city)

var _cooldown := 0.0

func _ready() -> void:
	collision_layer = 0
	collision_mask = 2
	var cs := CollisionShape3D.new()
	var sh := CylinderShape3D.new()
	sh.radius = 1.3
	sh.height = 3.0
	cs.shape = sh
	cs.position.y = 1.5
	add_child(cs)
	var pad := MeshInstance3D.new()
	var pad_mesh := CylinderMesh.new()
	pad_mesh.top_radius = 1.0
	pad_mesh.bottom_radius = 1.0
	pad_mesh.height = 0.1
	pad.mesh = pad_mesh
	var mat := StandardMaterial3D.new()
	var col := Color(0.2, 0.6, 1.0) if kind == "enter" else Color(0.1, 0.9, 0.35)
	mat.albedo_color = col
	mat.emission_enabled = true
	mat.emission = col
	mat.emission_energy_multiplier = 2.0
	pad.material_override = mat
	pad.position.y = 0.1
	add_child(pad)
	var light := OmniLight3D.new()
	light.light_color = col
	light.light_energy = 2.0
	light.omni_range = 9.0
	light.position.y = 1.8
	add_child(light)
	body_entered.connect(_on_body_entered)

func _process(delta: float) -> void:
	_cooldown = maxf(_cooldown - delta, 0.0)

func _on_body_entered(body: Node3D) -> void:
	if _cooldown > 0.0 or not body.is_in_group("player"):
		return
	_cooldown = 2.0
	Sfx.portal_use()
	_teleport_deferred(body)
	used.emit(kind)

func _teleport_deferred(body: Node3D) -> void:
	body.set_deferred("global_position", target)
	used.emit(kind + "_moved")
