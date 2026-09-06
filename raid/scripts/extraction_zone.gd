extends Area3D
## Extraction zone: glowing green beacon. Stand inside until the raid
## manager's timer completes to bank your loot.

signal player_entered
signal player_exited

const RADIUS := 2.6

func _ready() -> void:
	add_to_group("extraction")
	collision_layer = 0
	collision_mask = 2

	var cs := CollisionShape3D.new()
	var sh := CylinderShape3D.new()
	sh.radius = RADIUS
	sh.height = 4.0
	cs.shape = sh
	cs.position.y = 2.0
	add_child(cs)

	# Ground pad
	var pad := MeshInstance3D.new()
	var pad_mesh := CylinderMesh.new()
	pad_mesh.top_radius = RADIUS
	pad_mesh.bottom_radius = RADIUS
	pad_mesh.height = 0.12
	pad.mesh = pad_mesh
	var pad_mat := StandardMaterial3D.new()
	pad_mat.albedo_color = Color(0.1, 0.9, 0.35)
	pad_mat.emission_enabled = true
	pad_mat.emission = Color(0.1, 0.9, 0.35)
	pad_mat.emission_energy_multiplier = 1.6
	pad.material_override = pad_mat
	pad.position.y = 0.08
	add_child(pad)

	# Light beam so it reads from across the map
	var beam := MeshInstance3D.new()
	var beam_mesh := CylinderMesh.new()
	beam_mesh.top_radius = RADIUS * 0.55
	beam_mesh.bottom_radius = RADIUS * 0.8
	beam_mesh.height = 10.0
	beam.mesh = beam_mesh
	var beam_mat := StandardMaterial3D.new()
	beam_mat.albedo_color = Color(0.1, 1.0, 0.4, 0.16)
	beam_mat.emission_enabled = true
	beam_mat.emission = Color(0.1, 1.0, 0.4)
	beam_mat.emission_energy_multiplier = 1.2
	beam_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	beam_mat.cull_mode = BaseMaterial3D.CULL_FRONT
	beam_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	beam.material_override = beam_mat
	beam.position.y = 5.0
	beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(beam)

	var light := OmniLight3D.new()
	light.light_color = Color(0.2, 1.0, 0.45)
	light.light_energy = 2.5
	light.omni_range = 12.0
	light.position.y = 2.5
	add_child(light)

	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)

func _on_body_entered(body: Node3D) -> void:
	if body.is_in_group("player"):
		player_entered.emit()

func _on_body_exited(body: Node3D) -> void:
	if body.is_in_group("player"):
		player_exited.emit()


func scan_ping() -> void:
	## Scanner pulse: tag the extraction beam for a few seconds
	var label := Label3D.new()
	label.text = "EXTRACTION"
	label.font_size = 48
	label.pixel_size = 0.006
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	label.modulate = Color(0.2, 1.0, 0.45)
	label.outline_size = 10
	add_child(label)
	label.position.y = 10.5
	var t := create_tween()
	t.tween_interval(3.0)
	t.tween_property(label, "modulate:a", 0.0, 0.8)
	t.tween_callback(label.queue_free)
