extends Area3D
## Acid spit: green blob lobbed by facility spitters. Damages the player on
## contact, shatters on walls, expires after a short flight.

const SPEED := 14.0
const DAMAGE := 12.0
const LIFETIME := 3.0

var _dir := Vector3.FORWARD
var _life := LIFETIME

func launch(from: Vector3, target: Vector3) -> void:
	global_position = from
	_dir = (target - from).normalized()

func _ready() -> void:
	collision_layer = 0
	collision_mask = 1 | 2  # world shatters us, player takes the hit
	var cs := CollisionShape3D.new()
	var sh := SphereShape3D.new()
	sh.radius = 0.22
	cs.shape = sh
	add_child(cs)
	var mesh_inst := MeshInstance3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = 0.16
	mesh.height = 0.32
	mesh_inst.mesh = mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.4, 1.0, 0.3)
	mat.emission_enabled = true
	mat.emission = Color(0.35, 1.0, 0.25)
	mat.emission_energy_multiplier = 1.8
	mesh_inst.material_override = mat
	add_child(mesh_inst)
	var light := OmniLight3D.new()
	light.light_color = Color(0.4, 1.0, 0.3)
	light.light_energy = 1.2
	light.omni_range = 4.0
	light.shadow_enabled = false
	add_child(light)
	body_entered.connect(_on_body_entered)

func _physics_process(delta: float) -> void:
	global_position += _dir * SPEED * delta
	_life -= delta
	if _life <= 0.0:
		queue_free()

func _on_body_entered(body: Node3D) -> void:
	if body.is_in_group("player") and body.has_method("get_damage"):
		body.get_damage(DAMAGE)
		Sfx.flesh_hit(global_position)
	queue_free()
