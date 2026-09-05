extends Area3D
## Pickup crate: walk into it to collect.
## kind "loot" = money for the stash; kind "medkit" = heals on the spot.

signal collected(loot_value: int, box: Area3D)

const MODEL_LOOT := "res://assets/kaykit/city/box_A.gltf"
const MODEL_MEDKIT := "res://assets/kaykit/city/box_B.gltf"

@export_enum("loot", "medkit") var kind: String = "loot"
@export var loot_value: int = 50
@export var heal_amount: float = 40.0
@export var tint_color := Color(1, 1, 1)  # optional albedo tint (amber = facility scrap)

var _model: Node3D
var _t := randf() * TAU

func _ready() -> void:
	collision_layer = 0
	collision_mask = 2  # player layer
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = Vector3(1.3, 1.6, 1.3)
	cs.shape = sh
	cs.position.y = 0.8
	add_child(cs)
	var model_file := MODEL_MEDKIT if kind == "medkit" else MODEL_LOOT
	if ResourceLoader.exists(model_file):
		_model = (load(model_file) as PackedScene).instantiate()
		add_child(_model)
		_model.scale = Vector3.ONE * 1.2
		if kind == "medkit":
			_tint_model(Color(1.0, 0.35, 0.35))
		elif tint_color != Color(1, 1, 1):
			_tint_model(tint_color)
	body_entered.connect(_on_body_entered)

func _process(delta: float) -> void:
	_t += delta
	if _model:
		_model.rotation.y += delta * 1.2
		_model.position.y = absf(sin(_t * 2.0)) * 0.12

func _on_body_entered(body: Node3D) -> void:
	if body.is_in_group("player"):
		if kind == "medkit":
			Sfx.medkit_pickup(global_position)
			if body.has_method("get_heal"):
				body.get_heal(heal_amount)
		else:
			Sfx.loot_pickup(global_position)
		collected.emit(loot_value, self)
		queue_free()

func _tint_model(color: Color) -> void:
	for mi in _model.find_children("*", "MeshInstance3D", true, false):
		for i in mi.get_surface_override_material_count():
			var mesh: Mesh = mi.mesh
			if mesh == null:
				continue
			var src: Material = mesh.surface_get_material(i)
			if src == null:
				continue
			var tinted: Material = src.duplicate()
			if tinted is BaseMaterial3D:
				tinted.albedo_color = color
				tinted.emission_enabled = true
				tinted.emission = color * 0.4
			mi.set_surface_override_material(i, tinted)
