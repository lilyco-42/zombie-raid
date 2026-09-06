extends Node
## Lethal-Company-style facility: a drunkard-walk carved dungeon interior
## built from KayKit Dungeon Remastered pieces, far away from the city.
## Also places the city-side facility gate. Returns entrance/exit/cell data.

const DUN := "res://assets/kaykit/dungeon/"
const GRID := 10
const CELL := 6.0
const OFFSET := Vector3(120, 0, 120)
const GATE_POS := Vector3(-9, 0, -19.7)  # city block corner near player spawn

const WALL_VARIANTS := ["wall", "wall", "wall", "wall_cracked", "wall_broken"]

var _cache := {}
var rng := RandomNumberGenerator.new()

func build(world: Node3D, seed_value: int) -> Dictionary:
	rng.seed = seed_value
	_add_slab(world)
	var carved := _carve()
	var cells := _layout(world, carved)
	_add_city_gate(world)
	# Manager consumes world-space positions
	var world_cells: Array = []
	for c: Vector2i in cells:
		world_cells.append(_cell_world(c))
	return {
		"entrance": _cell_world(cells[0]),
		"exit": _cell_world(_farthest(carved, cells[0])),
		"cells": world_cells,
		"gate": GATE_POS,
	}

func _load(name: String) -> PackedScene:
	if not _cache.has(name):
		var path := DUN + name + ".glb"
		_cache[name] = load(path) if ResourceLoader.exists(path) else null
	return _cache[name]

func _place(world: Node3D, name: String, pos: Vector3, rot: Vector3, with_collision := true) -> Node3D:
	var scene := _load(name)
	if scene == null:
		return null
	var inst: Node3D = scene.instantiate()
	world.add_child(inst)
	inst.global_position = pos
	inst.rotation = rot
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

func _add_slab(world: Node3D) -> void:
	var body := StaticBody3D.new()
	body.name = "FacilitySlab"
	var size := GRID * CELL + 6.0
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(size, 1.0, size)
	shape.shape = box
	shape.position = Vector3(0, -0.5, 0)
	body.add_child(shape)
	body.position = OFFSET + Vector3(GRID * CELL * 0.5, 0, GRID * CELL * 0.5)
	world.add_child(body)

func _carve() -> Array:
	# Drunkard walk from a start cell until enough rooms are carved
	var cells := {}
	var cur := Vector2i(2, 2)
	cells[cur] = true
	var steps := 0
	while cells.size() < 42 and steps < 600:
		steps += 1
		var dir: Vector2i = [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN][rng.randi() % 4]
		var nxt: Vector2i = cur + dir
		if nxt.x < 0 or nxt.y < 0 or nxt.x >= GRID or nxt.y >= GRID:
			continue
		cur = nxt
		cells[cur] = true
	return cells.keys()

func _farthest(cells: Array, from: Vector2i) -> Vector2i:
	var best: Vector2i = from
	var best_d := -1
	for c: Vector2i in cells:
		var d: int = absi(c.x - from.x) + absi(c.y - from.y)
		if d > best_d:
			best_d = d
			best = c
	return best

func _cell_world(c: Vector2i) -> Vector3:
	return OFFSET + Vector3((c.x + 0.5) * CELL, 0, (c.y + 0.5) * CELL)

func _layout(world: Node3D, carved_cells: Array) -> Array:
	var carved := {}
	for c: Vector2i in carved_cells:
		carved[c] = true

	# Measure a wall and a floor tile once
	var probe := _place(world, "wall", Vector3(0, -80, 0), Vector3.ZERO, false)
	var wall_w := 2.0
	var wall_h := 3.5
	if probe:
		var b := _aabb_of(probe)
		if b.size.x > 0.1:
			wall_w = b.size.x
			wall_h = b.size.y
		probe.queue_free()
	var probe_f := _place(world, "floor_tile_large", Vector3(0, -80, 0), Vector3.ZERO, false)
	var floor_w := 2.0
	if probe_f:
		var fb := _aabb_of(probe_f)
		if fb.size.x > 0.1:
			floor_w = fb.size.x
		probe_f.queue_free()

	var ordered: Array = []
	for c: Vector2i in carved:
		ordered.append(c)

	for c: Vector2i in carved:
		var center := _cell_world(c)
		# Floor (visual only; slab below gives collision)
		var floor_name := "floor_tile_large" if rng.randf() < 0.8 else "floor_tile_large_rocks"
		_place(world, floor_name, center + Vector3(0, 0.03, 0),
			Vector3(0, float(rng.randi() % 4) * PI * 0.5, 0), false)
		# Ceiling (flipped floor, dark wood)
		_place(world, "floor_wood_large_dark", center + Vector3(0, wall_h + 0.08, 0),
			Vector3(PI, float(rng.randi() % 4) * PI * 0.5, 0), false)
		# Walls on every edge that faces an uncarved cell
		for dir in [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]:
			var nb: Vector2i = c + dir
			if carved.has(nb):
				continue
			var edge_center := center + Vector3(dir.x * CELL * 0.5, 0, dir.y * CELL * 0.5)
			var yaw := 0.0 if dir.y != 0 else PI * 0.5  # wall runs perpendicular to the edge normal
			var count := int(ceil(CELL / wall_w))
			for i in count:
				var along := Vector3(0, 0, 1) if dir.x != 0 else Vector3(1, 0, 0)
				var offset := (float(i) - float(count - 1) * 0.5) * wall_w
				var wpos := edge_center + along * offset
				_place(world, WALL_VARIANTS[rng.randi() % WALL_VARIANTS.size()], wpos, Vector3(0, yaw, 0))
		# Torch light on some inner edges
		if rng.randf() < 0.22:
			var tpos := center + Vector3(rng.randf_range(-2, 2), wall_h * 0.68, rng.randf_range(-2, 2))
			var torch := _place(world, "torch_lit", tpos, Vector3(0, rng.randf() * TAU, 0), false)
			if torch:
				var light := OmniLight3D.new()
				light.light_color = Color(1.0, 0.6, 0.25)
				light.light_energy = 1.9
				light.omni_range = 8.5
				light.shadow_enabled = false
				torch.add_child(light)
		# Dead-end treasure props (visual only; real pickups come from the manager)
		var open_dirs := 0
		for dir in [Vector2i.LEFT, Vector2i.RIGHT, Vector2i.UP, Vector2i.DOWN]:
			if carved.has(c + dir):
				open_dirs += 1
		if open_dirs == 1:
			var prop: String = ["chest", "chest_gold", "coin_stack_large", "coin_stack_medium"][rng.randi() % 4]
			_place(world, prop, center + Vector3(rng.randf_range(-1, 1), 0, rng.randf_range(-1, 1)),
				Vector3(0, rng.randf() * TAU, 0))
		elif rng.randf() < 0.25:
			var prop2: String = ["barrel_large", "box_large", "crates_stacked", "box_small"][rng.randi() % 4]
			var ppos := center + Vector3(rng.randf_range(-2, 2), 0, rng.randf_range(-2, 2))
			_place(world, prop2, ppos, Vector3(0, rng.randf() * TAU, 0))
	ordered.sort_custom(func(a, b): return _cell_world(a).length() < _cell_world(b).length())
	return ordered

func _add_city_gate(world: Node3D) -> void:
	# Arched gate in the city: visual frame; the manager drops the portal here
	_place(world, "wall_arched", GATE_POS, Vector3.ZERO)
	_place(world, "wall", GATE_POS + Vector3(-2.0, 0, 0), Vector3.ZERO)
	_place(world, "wall", GATE_POS + Vector3(2.0, 0, 0), Vector3.ZERO)
