extends Node
## Raid manager: the search-fight-extract loop.
## - Spawns zombies around the city (never on top of the player)
## - Scatters loot crates and free weapon pickups
## - Runs the extraction timer; success banks loot into Stash, death loses it
## - Restarts the raid scene after success/failure

const ZombieScene := preload("res://raid/scenes/zombie.tscn")
const LootBoxScript := preload("res://raid/scripts/loot_box.gd")
const ExtractionZoneScript := preload("res://raid/scripts/extraction_zone.gd")
const HUDScript := preload("res://raid/scripts/raid_hud.gd")
const PortalScript := preload("res://raid/scripts/portal.gd")

const WEAPON_SCENES := [
	"res://Player_Controller/Spawnable_Objects/Weapons/blasterQ.tscn",
	"res://Player_Controller/Spawnable_Objects/Weapons/blaster_I.tscn",
	"res://Player_Controller/Spawnable_Objects/Weapons/blaster_L.tscn",
	"res://Player_Controller/Spawnable_Objects/Weapons/blaster_m.tscn",
	"res://Player_Controller/Spawnable_Objects/Weapons/blaster_n.tscn",
]

const MAX_ALIVE_START := 6
const MAX_ALIVE_END := 14
const SPAWN_INTERVAL_START := 5.0
const SPAWN_INTERVAL_END := 2.2
const RAMP_SECONDS := 360.0
const EXTRACT_TIME := 3.0
const MIN_SPAWN_DIST := 18.0
const LOOT_COUNT := 9
const MEDKIT_COUNT := 3
const WEAPON_COUNT := 4
const FACILITY_SCRAP_COUNT := 12
const FACILITY_ZOMBIE_COUNT := 4
const SCRAP_TINT := Color(1.0, 0.8, 0.35)

# Zombie variants: weighted random pick at spawn (KayKit skeleton GLBs)
const VARIANTS := [
	{"name": "Runner", "model": "res://assets/kaykit/skeletons/Skeleton_Rogue.glb", "health": 40.0, "walk": 2.2, "run": 5.4, "damage": 10.0, "height": 1.6, "tint": Color(0.85, 1.0, 0.5), "weight": 3},
	{"name": "Walker", "model": "res://assets/kaykit/skeletons/Skeleton_Minion.glb", "health": 60.0, "walk": 1.7, "run": 4.0, "damage": 15.0, "height": 1.7, "tint": Color(0.62, 1.0, 0.62), "weight": 5},
	{"name": "Brute", "model": "res://assets/kaykit/skeletons/Skeleton_Warrior.glb", "health": 150.0, "walk": 1.3, "run": 3.1, "damage": 26.0, "height": 2.15, "tint": Color(0.9, 0.55, 0.5), "weight": 2},
]

var run_loot := 0
var kills := 0
var alive := 0
var elapsed := 0.0
var _run_over := false
var _in_zone := false
var _extract_t := 0.0
var _last_health := 100.0

var world: Node3D
var player: Node3D
var hud: CanvasLayer

func setup(world_ref: Node3D, player_ref: Node3D, block_centers: Array, dungeon: Dictionary = {}) -> void:
	world = world_ref
	player = player_ref
	hud = HUDScript.new()
	world.add_child(hud)
	if player.has_signal("player_died"):
		player.player_died.connect(_on_player_died)
	_last_health = player.current_health
	hud.set_health(player.current_health, player.max_health)
	hud.set_status(run_loot, Stash.banked_loot, kills, Stash.quota)

	var loot_spots := block_centers.duplicate()
	loot_spots.shuffle()
	var loot_slot_count := mini(LOOT_COUNT + MEDKIT_COUNT, loot_spots.size())
	for i in loot_slot_count:
		if i < MEDKIT_COUNT:
			_spawn_medkit(_corner_spot(loot_spots[i]))
		else:
			_spawn_loot_box(_corner_spot(loot_spots[i]), 40 + randi() % 60)
	var weapon_spots := block_centers.duplicate()
	weapon_spots.shuffle()
	for i in mini(WEAPON_COUNT, WEAPON_SCENES.size()):
		_spawn_weapon_pickup(WEAPON_SCENES[i], _corner_spot(weapon_spots[i]) + Vector3(0, 0.6, 0))
	_spawn_extraction_zone(Vector3(18.0, 0, 18.0))  # road junction: always clear
	if not dungeon.is_empty():
		_setup_facility(dungeon)
	hud.show_message("RAID START — loot the city, extract at the GREEN BEAM", 4.0)
	_run_spawner()

func _setup_facility(dungeon: Dictionary) -> void:
	# City gate portal -> inside; deep-in portal -> back outside
	var gate: Vector3 = dungeon["gate"]
	_spawn_portal(gate + Vector3(0, 0, 0.8), dungeon["entrance"], "enter")
	_spawn_portal(dungeon["exit"], gate + Vector3(0, 0, 2.2), "exit")
	# High-value scrap scattered in facility cells (skip the entrance cell area)
	var cells: Array = dungeon["cells"]
	var spots := cells.duplicate()
	spots.shuffle()
	var spawned := 0
	for cell in spots:
		if spawned >= FACILITY_SCRAP_COUNT:
			break
		var pos: Vector3 = cell
		if pos.distance_to(dungeon["entrance"]) < CELL_CLEARANCE:
			continue
		_spawn_loot_box(pos + Vector3(randf_range(-1.5, 1.5), 0, randf_range(-1.5, 1.5)), 90 + randi() % 80, SCRAP_TINT)
		spawned += 1
	# A few residents already inside
	var zombies_placed := 0
	for cell in spots:
		if zombies_placed >= FACILITY_ZOMBIE_COUNT:
			break
		var pos: Vector3 = cell
		if pos.distance_to(dungeon["entrance"]) < CELL_CLEARANCE * 2.0:
			continue
		_spawn_zombie_at(pos + Vector3(randf_range(-1.5, 1.5), 0.2, randf_range(-1.5, 1.5)))
		zombies_placed += 1

const CELL_CLEARANCE := 10.0

func _spawn_portal(pos: Vector3, target: Vector3, kind: String) -> void:
	var portal := Area3D.new()
	portal.set_script(PortalScript)
	portal.target = target
	portal.kind = kind
	world.add_child(portal)
	portal.global_position = pos
	portal.used.connect(func(k: String):
		if k.begins_with("enter"):
			hud.show_message("ENTERED THE FACILITY — grab the scrap, find the green EXIT portal", 3.5)
		elif k.begins_with("exit"):
			hud.show_message("BACK OUTSIDE — reach the GREEN BEAM to extract", 3.0)
	)

func _corner_spot(center: Vector3) -> Vector3:
	# Block-corner offset keeps items out of building footprints
	var sx := 1.0 if randf() < 0.5 else -1.0
	var sz := 1.0 if randf() < 0.5 else -1.0
	return center + Vector3(sx * 4.3, 0, sz * 4.3)

func _process(delta: float) -> void:
	if player == null or _run_over:
		return
	elapsed += delta
	# Health bar + damage flash (poll: the template player has no damaged signal)
	var hp: float = player.current_health
	if hp < _last_health:
		hud.damage_flash()
		Sfx.player_hurt()
	_last_health = hp
	hud.set_health(hp, player.max_health)
	# Extraction timer
	if _in_zone:
		_extract_t += delta
		hud.set_extraction(true, clampf(_extract_t / EXTRACT_TIME, 0.0, 1.0))
		if _extract_t >= EXTRACT_TIME:
			_extract_success()
	else:
		hud.set_extraction(false, 0.0)

func _difficulty() -> float:
	return clampf(elapsed / RAMP_SECONDS, 0.0, 1.0)

func _current_interval() -> float:
	return lerpf(SPAWN_INTERVAL_START, SPAWN_INTERVAL_END, _difficulty())

func _current_max_alive() -> int:
	return int(lerpf(MAX_ALIVE_START, MAX_ALIVE_END, _difficulty()))

func _pick_variant() -> Dictionary:
	var total := 0
	for v in VARIANTS:
		total += int(v["weight"])
	var roll := randi() % total
	for v in VARIANTS:
		roll -= int(v["weight"])
		if roll < 0:
			return v
	return VARIANTS[0]

func _run_spawner() -> void:
	var map_rid: RID = world.get_world_3d().navigation_map
	# Wait until the navmesh finished baking so agents get valid paths
	while NavigationServer3D.map_get_iteration_id(map_rid) == 0:
		await get_tree().create_timer(0.5).timeout
	while not _run_over:
		await get_tree().create_timer(_current_interval()).timeout
		if _run_over:
			return
		if alive < _current_max_alive():
			_spawn_zombie()

func _spawn_zombie() -> void:
	var spawn_points: Array = []
	var children := world.find_children("SpawnPoint*", "Node3D", true, false)
	if children.is_empty():
		return
	for sp in children:
		if sp.global_position.distance_to(player.global_position) > MIN_SPAWN_DIST:
			spawn_points.append(sp)
	var chosen: Node3D
	if spawn_points.is_empty():
		chosen = children[randi() % children.size()]
	else:
		chosen = spawn_points[randi() % spawn_points.size()]
	_spawn_zombie_at(chosen.global_position + Vector3(randf_range(-1.5, 1.5), 0.2, randf_range(-1.5, 1.5)))

func _spawn_zombie_at(pos: Vector3) -> void:
	var variant := _pick_variant()
	var zombie: CharacterBody3D = ZombieScene.instantiate()
	zombie.model_path = variant["model"]
	zombie.max_health = variant["health"]
	zombie.walk_speed = variant["walk"]
	zombie.run_speed = variant["run"]
	zombie.attack_damage = variant["damage"]
	zombie.body_height = variant["height"]
	zombie.tint = variant["tint"]
	world.add_child(zombie)
	zombie.global_position = pos
	zombie.died.connect(_on_zombie_died)
	alive += 1
	if variant["name"] == "Brute":
		hud.show_message("A BRUTE is out there...", 1.5)

func _on_zombie_died(at_position: Vector3) -> void:
	alive = maxi(alive - 1, 0)
	kills += 1
	Stash.lifetime_kills += 1
	hud.set_status(run_loot, Stash.banked_loot, kills, Stash.quota)
	if randf() < 0.3:
		_spawn_loot_box(at_position, 30 + randi() % 50)

func _spawn_loot_box(pos: Vector3, value: int, tint := Color(1, 1, 1)) -> void:
	var box := Area3D.new()
	box.set_script(LootBoxScript)
	box.loot_value = value
	if tint != Color(1, 1, 1):
		box.tint_color = tint
	world.add_child(box)
	box.global_position = Vector3(pos.x, 0.0, pos.z)
	box.collected.connect(_on_loot_collected)

func _spawn_medkit(pos: Vector3) -> void:
	var box := Area3D.new()
	box.set_script(LootBoxScript)
	box.kind = "medkit"
	world.add_child(box)
	box.global_position = Vector3(pos.x, 0.0, pos.z)
	box.collected.connect(_on_loot_collected)

func _on_loot_collected(value: int, box: Area3D) -> void:
	if box.get("kind") == "medkit":
		hud.show_message("+ %d HP" % int(box.get("heal_amount")), 1.0)
	else:
		run_loot += value
		hud.show_message("+ $%d" % value, 1.0)
	hud.set_status(run_loot, Stash.banked_loot, kills, Stash.quota)

func _spawn_weapon_pickup(path: String, pos: Vector3) -> void:
	if not ResourceLoader.exists(path):
		return
	var scene: PackedScene = load(path)
	if scene == null:
		return
	var inst: Node3D = scene.instantiate()
	world.add_child(inst)
	inst.global_position = pos

var _extract_hum: AudioStreamPlayer3D

func _spawn_extraction_zone(pos: Vector3) -> void:
	var zone := Area3D.new()
	zone.set_script(ExtractionZoneScript)
	world.add_child(zone)
	zone.global_position = pos
	zone.player_entered.connect(func(): _in_zone = true)
	zone.player_exited.connect(func():
		_in_zone = false
		_extract_t = 0.0
	)
	_extract_hum = Sfx.make_loop_3d(Sfx.DIR + "kenney/forceField_001.ogg", -8.0)
	if _extract_hum:
		world.add_child(_extract_hum)
		_extract_hum.global_position = pos + Vector3(0, 1.5, 0)
		_extract_hum.play()

func _extract_success() -> void:
	_run_over = true
	Stash.banked_loot += run_loot
	Stash.successful_extractions += 1
	Sfx.extract_success()
	hud.set_extraction(false, 0.0)
	var quota_msg := ""
	if Stash.banked_loot >= Stash.quota:
		Stash.quota *= 2
		quota_msg = "  QUOTA MET — doubled to $%d!" % Stash.quota
	hud.show_message("EXTRACTION SUCCESSFUL  +$%d  (stash $%d / quota $%d)%s" % [run_loot, Stash.banked_loot, Stash.quota, quota_msg], 4.0)
	await get_tree().create_timer(4.0).timeout
	get_tree().reload_current_scene()

func _on_player_died() -> void:
	if _run_over:
		return
	_run_over = true
	_run_loot_lost()
	Sfx.raid_failed()
	hud.set_extraction(false, 0.0)
	hud.show_message("YOU DIED — carried loot lost", 4.0)
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
	await get_tree().create_timer(4.0).timeout
	get_tree().reload_current_scene()

func _run_loot_lost() -> void:
	pass  # dying simply discards run_loot; stash stays untouched
