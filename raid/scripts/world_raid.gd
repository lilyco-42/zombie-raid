extends Node3D
## Raid map orchestrator: builds the city, bakes the navmesh,
## seeds zombie spawn points, then hands over to the raid manager.

const CityBuilderScript := preload("res://raid/scripts/city_builder.gd")
const AvatarScript := preload("res://raid/scripts/player_avatar.gd")
const DungeonBuilderScript := preload("res://raid/scripts/dungeon_builder.gd")
const TouchControlsScript := preload("res://raid/scripts/touch_controls.gd")

@onready var player: CharacterBody3D = $PlayerInstance
@onready var manager: Node = $Manager

func _ready() -> void:
	player.add_to_group("player")
	var avatar: Node3D = AvatarScript.new()
	avatar.name = "PlayerAvatar"
	player.add_child(avatar)
	if DisplayServer.is_touchscreen_available():
		var touch := CanvasLayer.new()
		touch.name = "TouchControls"
		touch.set_script(TouchControlsScript)
		add_child(touch)
	var ambient := Sfx.make_loop_ui(Sfx.DIR + "kenney/spaceEngineLow_002.ogg", -22.0)
	if ambient:
		add_child(ambient)
		ambient.play()
	var builder := Node.new()
	builder.set_script(CityBuilderScript)
	add_child(builder)
	var info: Dictionary = builder.build(self)

	var dungeon_builder := Node.new()
	dungeon_builder.name = "DungeonBuilder"
	dungeon_builder.set_script(DungeonBuilderScript)
	add_child(dungeon_builder)
	var dungeon: Dictionary = dungeon_builder.build(self, randi())

	_seed_spawn_points(info["block_centers"])
	_setup_navigation()
	manager.setup(self, player, info["block_centers"], dungeon)

func _seed_spawn_points(block_centers: Array) -> void:
	var spots := block_centers.duplicate()
	spots.shuffle()
	var count := mini(10, spots.size())
	for i in count:
		var sp := Node3D.new()
		sp.name = "SpawnPoint_%02d" % i
		add_child(sp)
		# Block corner offset keeps spawns out of building footprints
		var base: Vector3 = spots[i] + Vector3(_rand_sign() * 4.3, 0.1, _rand_sign() * 4.3)
		sp.global_position = base

func _rand_sign() -> float:
	return 1.0 if randf() < 0.5 else -1.0

func _setup_navigation() -> void:
	var nav_region := NavigationRegion3D.new()
	nav_region.name = "NavRegion"
	var nm := NavigationMesh.new()
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nm.geometry_collision_mask = 1
	nm.agent_radius = 0.45
	nm.agent_height = 1.8
	nm.agent_max_climb = 0.5
	nm.cell_size = 0.3
	nm.cell_height = 0.3
	nav_region.navigation_mesh = nm
	add_child(nav_region)
	_bake_navmesh(nav_region)

func _bake_navmesh(region: NavigationRegion3D) -> void:
	await get_tree().physics_frame
	await get_tree().physics_frame
	# Sync bake on the web (threaded baking is unreliable there); threaded elsewhere
	region.bake_navigation_mesh(not OS.has_feature("web"))
