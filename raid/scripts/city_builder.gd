extends Node
## Procedurally assembles the city map from KayKit City Builder Bits (CC0).
## Roads on a grid, one building per block, props + parked cars + streetlights.
## Every placed model gets trimesh collision so bullets and the navmesh see it.

const CITY := "res://assets/kaykit/city/"
const MAP_HALF := 30.0
const ROAD_LINES := [-18.0, 0.0, 18.0]
const ROAD_STEP := 6.0

const BUILDINGS := ["building_A", "building_B", "building_C", "building_D", "building_E", "building_F", "building_G", "building_H"]
const PROPS := ["dumpster", "bench", "box_A", "box_B", "trash_A", "trash_B", "bush", "firehydrant"]
const CARS := ["car_hatchback", "car_police", "car_sedan", "car_stationwagon", "car_taxi"]

var _model_cache := {}

func build(world: Node3D) -> Dictionary:
	_add_ground(world)
	_add_walls(world)
	_add_roads(world)
	var block_centers := _add_blocks(world)
	_add_cars(world)
	_add_streetlights(world)
	return {"block_centers": block_centers}

func _load_model(name: String) -> PackedScene:
	if not _model_cache.has(name):
		var path := CITY + name + ".gltf"
		if ResourceLoader.exists(path):
			_model_cache[name] = load(path)
		else:
			push_warning("City model missing: " + path)
			_model_cache[name] = null
	return _model_cache[name]

func _place(world: Node3D, name: String, pos: Vector3, yaw: float, with_collision := true) -> Node3D:
	var scene := _load_model(name)
	if scene == null:
		return null
	var inst: Node3D = scene.instantiate()
	world.add_child(inst)
	inst.global_position = pos
	inst.rotation.y = yaw
	if with_collision:
		for mi in inst.find_children("*", "MeshInstance3D", true, false):
			mi.create_trimesh_collision()
	return inst

func _aabb_of(inst: Node3D) -> AABB:
	var total := AABB()
	var has := false
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		var rel: Transform3D = inst.global_transform.affine_inverse() * mi.global_transform
		var box: AABB = rel * mi.get_aabb()
		total = box if not has else total.merge(box)
		has = true
	return total

func _add_ground(world: Node3D) -> void:
	var body := StaticBody3D.new()
	body.name = "Ground"
	var size := (MAP_HALF + 4.0) * 2.0
	var mesh_inst := MeshInstance3D.new()
	var box_mesh := BoxMesh.new()
	box_mesh.size = Vector3(size, 1.0, size)
	mesh_inst.mesh = box_mesh
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.14, 0.14, 0.16)
	mat.roughness = 1.0
	mesh_inst.material_override = mat
	mesh_inst.position.y = -0.5
	body.add_child(mesh_inst)
	var shape := CollisionShape3D.new()
	var box_shape := BoxShape3D.new()
	box_shape.size = Vector3(size, 1.0, size)
	shape.shape = box_shape
	shape.position.y = -0.5
	body.add_child(shape)
	world.add_child(body)

func _add_walls(world: Node3D) -> void:
	var edge := MAP_HALF + 3.5
	var wall_mat := StandardMaterial3D.new()
	wall_mat.albedo_color = Color(0.3, 0.3, 0.33)
	wall_mat.roughness = 0.9
	var configs := [
		{"pos": Vector3(0, 3.5, -edge), "size": Vector3(edge * 2.0, 7.0, 1.0)},
		{"pos": Vector3(0, 3.5, edge), "size": Vector3(edge * 2.0, 7.0, 1.0)},
		{"pos": Vector3(-edge, 3.5, 0), "size": Vector3(1.0, 7.0, edge * 2.0)},
		{"pos": Vector3(edge, 3.5, 0), "size": Vector3(1.0, 7.0, edge * 2.0)},
	]
	for cfg in configs:
		var body := StaticBody3D.new()
		body.name = "BoundaryWall"
		var mesh_inst := MeshInstance3D.new()
		var box_mesh := BoxMesh.new()
		box_mesh.size = cfg["size"]
		mesh_inst.mesh = box_mesh
		mesh_inst.material_override = wall_mat
		body.add_child(mesh_inst)
		var shape := CollisionShape3D.new()
		var box_shape := BoxShape3D.new()
		box_shape.size = cfg["size"]
		shape.shape = box_shape
		body.add_child(shape)
		body.position = cfg["pos"]
		world.add_child(body)

func _add_roads(world: Node3D) -> void:
	# Measure a straight piece once to learn its tile size, then scale to ROAD_STEP
	var probe := _place(world, "road_straight", Vector3(0, -50, 0), 0.0, false)
	var tile := 6.0
	if probe:
		var box := _aabb_of(probe)
		if box.size.x > 0.1:
			tile = box.size.x
		probe.queue_free()
	# X-running roads (along X axis, fixed z) and Z-running roads
	for c in ROAD_LINES:
		var x := -MAP_HALF
		while x <= MAP_HALF:
			var at_crossing := ROAD_LINES.has(x)
			var pos := Vector3(x, 0.03, c)
			if at_crossing:
				_place_road(world, "road_junction", pos, tile)
			else:
				_place_road(world, "road_straight", pos, tile)
			x += ROAD_STEP
		var z := -MAP_HALF
		while z <= MAP_HALF:
			if ROAD_LINES.has(z):
				z += ROAD_STEP
				continue
			_place_road(world, "road_straight", Vector3(c, 0.03, z), tile, PI * 0.5)
			z += ROAD_STEP

func _place_road(world: Node3D, name: String, pos: Vector3, tile: float, yaw := 0.0) -> void:
	var inst := _place(world, name, pos, yaw, false)
	if inst == null:
		return
	var box := _aabb_of(inst)
	if box.size.x > 0.1:
		var s := tile / box.size.x
		inst.scale = Vector3(s, 1.0, s)

func _add_blocks(world: Node3D) -> Array:
	var centers := []
	var axis_vals := [-24.0, -9.0, 9.0, 24.0]
	for bx in axis_vals:
		for bz in axis_vals:
			centers.append(Vector3(bx, 0, bz))
	var park_center := Vector3.INF
	for center: Vector3 in centers:
		var is_park := randf() < 0.14
		if is_park:
			park_center = center
			for i in 5:
				var p := center + Vector3(randf_range(-4.5, 4.5), 0, randf_range(-4.5, 4.5))
				_place(world, "bush", p, randf() * TAU)
			continue
		var building: String = BUILDINGS[randi() % BUILDINGS.size()]
		var yaw: float = (PI * 0.5) * float(randi() % 4)
		var bpos := center + Vector3(randf_range(-0.8, 0.8), 0, randf_range(-0.8, 0.8))
		_place(world, building, bpos, yaw)
		# Scatter props around the building
		var prop_count := 3 + randi() % 4
		for i in prop_count:
			var prop: String = PROPS[randi() % PROPS.size()]
			var angle := randf() * TAU
			var radius := randf_range(3.2, 5.2)
			var ppos := center + Vector3(cos(angle) * radius, 0, sin(angle) * radius)
			ppos.x = clampf(ppos.x, -MAP_HALF + 2.0, MAP_HALF - 2.0)
			ppos.z = clampf(ppos.z, -MAP_HALF + 2.0, MAP_HALF - 2.0)
			_place(world, prop, ppos, randf() * TAU)
	# Landmark: watertower goes on the park block only (never on a building)
	if park_center != Vector3.INF:
		_place(world, "watertower", park_center, randf() * TAU)
	return centers

func _add_cars(world: Node3D) -> void:
	for c in ROAD_LINES:
		# Cars parked along X-roads
		for i in 2:
			var cx := randf_range(-MAP_HALF + 4, MAP_HALF - 4)
			var lane: float = 2.1 if randf() < 0.5 else -2.1
			var yaw: float = PI * 0.5 + randf_range(-0.15, 0.15)
			_place(world, CARS[randi() % CARS.size()], Vector3(cx, 0.05, c + lane), yaw)
		# Cars parked along Z-roads
		for i in 2:
			var cz := randf_range(-MAP_HALF + 4, MAP_HALF - 4)
			var lane_z: float = 2.1 if randf() < 0.5 else -2.1
			var yaw_z: float = randf_range(-0.15, 0.15)
			_place(world, CARS[randi() % CARS.size()], Vector3(c + lane_z, 0.05, cz), yaw_z)

func _add_streetlights(world: Node3D) -> void:
	for cx in ROAD_LINES:
		for cz in ROAD_LINES:
			var corner := Vector3(cx + 3.6, 0, cz + 3.6)
			var lamp := _place(world, "streetlight", corner, PI * 0.75)
			if lamp:
				var light := OmniLight3D.new()
				light.light_color = Color(1.0, 0.85, 0.6)
				light.light_energy = 2.2
				light.omni_range = 13.0
				light.position = Vector3(0, 4.4, 0)
				light.shadow_enabled = false
				lamp.add_child(light)
