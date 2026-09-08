extends Area3D
## Pickup crate: walk into it to collect.
## kind "loot" = money for the stash; kind "medkit" = heals on the spot.

signal collected(loot_value: int, box: Area3D)

const MODEL_LOOT := "res://assets/kaykit/city/box_A.gltf"
const MODEL_MEDKIT := "res://assets/kaykit/city/box_B.gltf"
## 中式旧物废料线 (设施高价值 scrap): 每次生成随机抽一件
const RELIC_MODELS: Array[String] = [
	"res://assets/static/vendor/chinese/thermos_bottle.glb",
	"res://assets/static/vendor/chinese/enamel_mug.glb",
	"res://assets/static/vendor/chinese/tin_can.glb",
	"res://assets/static/vendor/chinese/ration_bundle.glb",
	# 第二批: 家书 / 工牌 / 半玉佩 / 老收音机
	"res://assets/static/vendor/chinese/old_letter.glb",
	"res://assets/static/vendor/chinese/work_badge.glb",
	"res://assets/static/vendor/chinese/half_jade.glb",
	"res://assets/static/vendor/chinese/old_radio.glb",
	# 第三批: 算盘 / 煤油灯 / 搪瓷痰盂 / 留声机
	"res://assets/static/vendor/chinese/abacus.glb",
	"res://assets/static/vendor/chinese/kerosene_lamp.glb",
	"res://assets/static/vendor/chinese/enamel_spittoon.glb",
	"res://assets/static/vendor/chinese/gramophone.glb",
]

@export_enum("loot", "medkit", "relic") var kind: String = "loot"
@export var loot_value: int = 50
@export var heal_amount: float = 40.0
@export var tint_color := Color(1, 1, 1)  # optional albedo tint (amber = facility scrap)

var _model: Node3D
var _t := randf() * TAU

func _ready() -> void:
	add_to_group("loot")
	collision_layer = 0
	collision_mask = 2  # player layer
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = Vector3(1.3, 1.6, 1.3)
	cs.shape = sh
	cs.position.y = 0.8
	add_child(cs)
	var model_file := MODEL_LOOT
	if kind == "relic":
		model_file = RELIC_MODELS[randi() % RELIC_MODELS.size()]
	elif kind == "medkit":
		model_file = MODEL_MEDKIT
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


func scan_ping(player_pos: Vector3) -> void:
	## Scanner pulse: float a value+distance tag above the crate for a few seconds
	if kind == "medkit":
		return  # medkits stay subtle
	var dist := int(global_position.distance_to(player_pos))
	var label := Label3D.new()
	label.text = "$%d  |  %dm" % [loot_value, dist]
	label.font_size = 42
	label.pixel_size = 0.006
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.modulate = Color(1.0, 0.85, 0.3)
	label.outline_size = 10
	add_child(label)
	label.position.y = 1.6
	var t := create_tween()
	t.tween_interval(3.0)
	t.tween_property(label, "modulate:a", 0.0, 0.8)
	t.tween_callback(label.queue_free)
	if _model:
		var pulse := create_tween()
		pulse.tween_property(_model, "scale", _model.scale * 1.25, 0.15)
		pulse.tween_property(_model, "scale", _model.scale, 0.35)
