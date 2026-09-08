extends Node
## Raid manager: the search-fight-extract loop.
## - Spawns zombies around the city (never on top of the player)
## - Scatters loot crates and free weapon pickups
## - Runs the extraction timer; success banks loot into Stash, death loses it
## - Restarts the raid scene after success/failure

const ZombieScene := preload("res://game/scenes/zombie.tscn")
const SpitterScript := preload("res://game/scripts/spitter.gd")
const SPITTER_MODEL := "res://assets/kaykit/skeletons/Skeleton_Mage.glb"
const LootBoxScript := preload("res://game/scripts/loot_box.gd")
const ExtractionZoneScript := preload("res://game/scripts/extraction_zone.gd")
const HUDScript := preload("res://game/scripts/raid_hud.gd")
const I18n := preload("res://game/scripts/i18n.gd")
const AmmoPickupScript := preload("res://game/scripts/ammo_pickup.gd")
const AMMO_COUNT := 8
const PortalScript := preload("res://game/scripts/portal.gd")

const WEAPON_SCENES := [
	"res://vendor/Player_Controller/Spawnable_Objects/Weapons/blasterQ.tscn",
	"res://vendor/Player_Controller/Spawnable_Objects/Weapons/blaster_I.tscn",
	"res://vendor/Player_Controller/Spawnable_Objects/Weapons/blaster_L.tscn",
	"res://vendor/Player_Controller/Spawnable_Objects/Weapons/blaster_m.tscn",
	"res://vendor/Player_Controller/Spawnable_Objects/Weapons/blaster_n.tscn",
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
const FACILITY_SPITTERS := 3   # of the facility residents, these spit acid
const SCRAP_TINT := Color(1.0, 0.8, 0.35)
const RUN_LIMIT := 480.0       # seconds until the moon leaves
const FRENZY_GRACE := 90.0     # frenzy phase before the run is lost

# Zombie variants: weighted random pick at spawn (KayKit skeleton GLBs)
const VARIANTS := [
	{"name": "Runner", "model": "res://assets/kaykit/skeletons/Skeleton_Rogue.glb", "health": 40.0, "walk": 2.2, "run": 5.4, "damage": 10.0, "height": 1.6, "tint": Color(0.85, 1.0, 0.5), "weight": 3},
	{"name": "Walker", "model": "res://assets/kaykit/skeletons/Skeleton_Minion.glb", "health": 60.0, "walk": 1.7, "run": 4.0, "damage": 15.0, "height": 1.7, "tint": Color(0.62, 1.0, 0.62), "weight": 5},
	{"name": "Brute", "model": "res://assets/kaykit/skeletons/Skeleton_Warrior.glb", "health": 150.0, "walk": 1.3, "run": 3.1, "damage": 26.0, "height": 2.15, "tint": Color(0.9, 0.55, 0.5), "weight": 2},
]

var run_loot := 0
var loot_bonus := 1.0    # shop upgrade: multiplier on collected loot value
var speed_bonus := 0.0   # shop upgrade: offsets the loot weight penalty
var kills := 0
var alive := 0
var elapsed := 0.0
var _run_over := false
var _in_zone := false
var _extract_t := 0.0
var _last_health := 100.0
var _frenzy := false
var _scan_cd := 0.0

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
	Net.raid_failed_net.connect(net_raid_failed)
	Net.extract_success_net.connect(net_extract_success)
	_last_health = player.current_health
	hud.set_health(player.current_health, player.max_health)
	hud.set_status(run_loot, Stash.banked_loot, kills, Stash.quota)
	_connect_ammo_hud()

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
	for i in AMMO_COUNT:
		var ammo_idx := (WEAPON_COUNT + i) % weapon_spots.size()
		_spawn_ammo_pickup(_corner_spot(weapon_spots[ammo_idx]))
	_spawn_extraction_zone(Vector3(18.0, 0, 18.0))  # road junction: always clear
	if not dungeon.is_empty():
		_setup_facility(dungeon)
	hud.show_message(I18n.t("raid_start"), 4.0)
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
		_spawn_relic(pos + Vector3(randf_range(-1.5, 1.5), 0, randf_range(-1.5, 1.5)), 90 + randi() % 80)
		spawned += 1
	# A few residents already inside
	var zombies_placed := 0
	var spitters_placed := 0
	var spitter_announced := false
	for cell in spots:
		if zombies_placed >= FACILITY_ZOMBIE_COUNT:
			break
		var pos: Vector3 = cell
		if pos.distance_to(dungeon["entrance"]) < CELL_CLEARANCE * 2.0:
			continue
		if spitters_placed < FACILITY_SPITTERS:
			_spawn_spitter_at(pos + Vector3(randf_range(-1.5, 1.5), 0.2, randf_range(-1.5, 1.5)))
			spitters_placed += 1
			if not spitter_announced:
				spitter_announced = true
			hud.show_message(I18n.t("spitter_warning"), 2.0)
		else:
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

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("scan"):
		_do_scan()

func _do_scan() -> void:
	if _scan_cd > 0.0 or _run_over:
		return
	_scan_cd = 2.0
	Sfx.scan(player.global_position)
	for box in get_tree().get_nodes_in_group("loot"):
		box.scan_ping(player.global_position)
	for zone in get_tree().get_nodes_in_group("extraction"):
		zone.scan_ping()

func _process(delta: float) -> void:
	if player == null or _run_over:
		return
	elapsed += delta
	_scan_cd = maxf(_scan_cd - delta, 0.0)
	# Loot weight: carrying more slows you down (Lethal Company style)
	player.weight_factor = clampf((1.0 + speed_bonus) - float(run_loot) / 2400.0 * 0.35, 0.65, 1.4)
	# Moon countdown
	var remaining := RUN_LIMIT - elapsed
	if remaining > 0.0:
		hud.set_clock("T-%d:%02d TO SUNRISE" % [int(remaining) / 60, int(remaining) % 60], remaining < 60.0)
	else:
		var grace := RUN_LIMIT + FRENZY_GRACE - elapsed
		hud.set_clock("FRENZY  %d:%02d" % [int(maxf(grace, 0.0)) / 60, int(maxf(grace, 0.0)) % 60], true)
		if grace <= 0.0:
			player.get_damage(99999.0)
			return
	if elapsed >= RUN_LIMIT and not _frenzy:
		_trigger_frenzy()
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

func _trigger_frenzy() -> void:
	_frenzy = true
	Sfx.frenzy_stinger()
	hud.show_message("THE MOON IS LEAVING — EVERYTHING HUNTS YOU", 5.0)
	for z in get_tree().get_nodes_in_group("zombie"):
		z.frenzy()

func net_sync_clock(net_elapsed: float, frenzy_now: bool) -> void:
	## Client: 1 Hz host broadcast keeps the raid clock + frenzy phase in sync
	elapsed = net_elapsed
	if frenzy_now and not _frenzy:
		_trigger_frenzy()

func _difficulty() -> float:
	return clampf(elapsed / RAMP_SECONDS, 0.0, 1.0)

func _current_interval() -> float:
	return lerpf(SPAWN_INTERVAL_START, SPAWN_INTERVAL_END, _difficulty())

func _current_max_alive() -> int:
	return int(lerpf(MAX_ALIVE_START, MAX_ALIVE_END, _difficulty()))

func _pick_variant_index() -> int:
	var total := 0
	for v in VARIANTS:
		total += int(v["weight"])
	var roll := randi() % total
	for i in VARIANTS.size():
		roll -= int(VARIANTS[i]["weight"])
		if roll < 0:
			return i
	return 0

func _run_spawner() -> void:
	if Net.online and not Net.is_host():
		return  # clients only mirror zombies; the host spawns for everyone
	var map_rid: RID = world.get_world_3d().navigation_map
	# Wait for the navmesh (max 10s); after that zombies fall back to direct steering
	var waited := 0.0
	while NavigationServer3D.map_get_iteration_id(map_rid) == 0 and waited < 10.0:
		await get_tree().create_timer(0.5).timeout
		waited += 0.5
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

func _spawn_spitter_at(pos: Vector3) -> void:
	var spitter: CharacterBody3D = _make_spitter()
	if Net.online:
		spitter.net_id = Net.next_net_id()
		spitter.name = "Z_%d" % spitter.net_id
	world.add_child(spitter)
	spitter.global_position = pos
	spitter.died.connect(_on_zombie_died.bind(spitter))
	alive += 1

func _make_spitter() -> CharacterBody3D:
	var spitter: CharacterBody3D = ZombieScene.instantiate()
	spitter.set_script(SpitterScript)
	spitter.model_path = SPITTER_MODEL
	spitter.max_health = 45.0
	spitter.walk_speed = 1.3
	spitter.run_speed = 3.4
	spitter.attack_damage = 12.0
	spitter.body_height = 1.75
	spitter.tint = Color(0.75, 0.6, 1.0)
	spitter.ztype = 3
	return spitter

func _spawn_zombie_at(pos: Vector3, variant_idx := -1) -> void:
	if variant_idx < 0:
		variant_idx = _pick_variant_index()
	var variant: Dictionary = VARIANTS[variant_idx]
	var zombie: CharacterBody3D = ZombieScene.instantiate()
	zombie.ztype = variant_idx
	zombie.model_path = variant["model"]
	zombie.max_health = variant["health"]
	zombie.walk_speed = variant["walk"]
	zombie.run_speed = variant["run"]
	zombie.attack_damage = variant["damage"]
	zombie.body_height = variant["height"]
	zombie.tint = variant["tint"]
	if Net.online:
		zombie.net_id = Net.next_net_id()
		zombie.name = "Z_%d" % zombie.net_id
	world.add_child(zombie)
	zombie.global_position = pos
	zombie.died.connect(_on_zombie_died.bind(zombie))
	alive += 1
	if _frenzy:
		zombie.frenzy()
	if variant["name"] == "Brute":
		hud.show_message("A BRUTE is out there...", 1.5)

func net_spawn_mirror(id: int, pos: Vector3, type: int) -> void:
	## Client side: the host broadcast mentioned a zombie we don't have yet
	if _zombie_by_net_id(id) != null:
		return
	var zombie: CharacterBody3D
	if type == 3:
		zombie = _make_spitter()
	else:
		var v: Dictionary = VARIANTS[clampi(type, 0, VARIANTS.size() - 1)]
		zombie = ZombieScene.instantiate()
		zombie.ztype = clampi(type, 0, VARIANTS.size() - 1)
		zombie.model_path = v["model"]
		zombie.max_health = v["health"]
		zombie.walk_speed = v["walk"]
		zombie.run_speed = v["run"]
		zombie.attack_damage = v["damage"]
		zombie.body_height = v["height"]
		zombie.tint = v["tint"]
	zombie.net_id = id
	zombie.name = "Z_%d" % id
	zombie._has_net = true  # skip the spawn intro; drives interpolation playback
	world.add_child(zombie)
	zombie.global_position = pos
	alive += 1

func _zombie_by_net_id(id: int) -> Node:
	return world.get_node_or_null(NodePath("Z_%d" % id))

func _on_zombie_died(at_position: Vector3, z: Node = null) -> void:
	alive = maxi(alive - 1, 0)
	kills += 1
	Stash.lifetime_kills += 1
	hud.set_status(run_loot, Stash.banked_loot, kills, Stash.quota)
	var drop_value := 0
	if randf() < 0.3:
		drop_value = 30 + randi() % 50
		_spawn_loot_box(at_position, drop_value)
	if Net.online and z != null and int(z.get("net_id")) > 0:
		Net.rpc("rpc_zombie_dead", int(z.get("net_id")), at_position, drop_value)

func net_on_zombie_dead(pos: Vector3, drop_value: int) -> void:
	## Client side: the host reports a zombie died (kill credit + loot mirror)
	kills += 1
	hud.set_status(run_loot, Stash.banked_loot, kills, Stash.quota)
	if drop_value > 0:
		_spawn_loot_box(pos, drop_value)

func _connect_ammo_hud() -> void:
	var wm := player.find_child("Weapons_Manager", true, false)
	if wm == null or not wm.has_signal("update_ammo"):
		return
	wm.update_ammo.connect(func(a): hud.set_ammo(int(a[0]), int(a[1])))
	var slot: Resource = wm.get("current_weapon_slot")
	if slot:
		hud.set_ammo(int(slot.get("current_ammo")), int(slot.get("reserve_ammo")))

func _spawn_ammo_pickup(pos: Vector3) -> void:
	var box: Area3D = AmmoPickupScript.new()
	world.add_child(box)
	box.global_position = pos
	box.collected.connect(_on_ammo_collected)

func _on_ammo_collected(amount: int, _box: Area3D) -> void:
	hud.show_message(I18n.t("ammo_gained") % amount, 1.6)

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

func _spawn_relic(pos: Vector3, value: int) -> void:
	## 中式旧物 (暖水瓶/搪瓷缸/铁皮罐头/粮票捆): 设施深处的"被遗忘的生活",
	## 数值对齐原 scrap 档 (90-170), 模型在 loot_box 内随机抽。
	var box := Area3D.new()
	box.set_script(LootBoxScript)
	box.kind = "relic"
	box.loot_value = value
	world.add_child(box)
	box.global_position = Vector3(pos.x, 0.0, pos.z)
	box.collected.connect(_on_loot_collected)

func _on_loot_collected(value: int, box: Area3D) -> void:
	Net.claim_box(box.global_position)  # first taker wins; no-op offline
	if box.get("kind") == "medkit":
		hud.show_message("+ %d HP" % int(box.get("heal_amount")), 1.0)
	else:
		run_loot += int(round(value * loot_bonus))
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
	## Local player finished the extraction timer. Online: host broadcasts
	## team success; clients report to the host who then broadcasts.
	if _run_over:
		return
	_run_over = true
	_stash_extraction()
	if Net.online:
		if Net.is_host():
			Net.rpc("rpc_extract_success")
		else:
			Net.rpc("rpc_report_extract", true)
	_end_raid()

func net_extract_success() -> void:
	## Received: someone on the team extracted — bank your own loot too
	if _run_over:
		return
	_run_over = true
	_stash_extraction()
	_end_raid()

func net_extract_report() -> void:
	## Host: a client reports a completed extraction -> team success
	if _run_over:
		return
	_extract_success()

func _stash_extraction() -> void:
	Stash.banked_loot += run_loot
	Stash.successful_extractions += 1
	Sfx.extract_success()
	hud.set_extraction(false, 0.0)
	var quota_msg := ""
	if Stash.banked_loot >= Stash.quota:
		Stash.quota *= 2
		quota_msg = "  QUOTA MET — doubled to $%d!" % Stash.quota
	hud.show_message("EXTRACTION SUCCESSFUL  +$%d  (stash $%d / quota $%d)%s" % [run_loot, Stash.banked_loot, Stash.quota, quota_msg], 4.0)

func _end_raid() -> void:
	await get_tree().create_timer(4.0).timeout
	get_tree().reload_current_scene()

func _on_player_died() -> void:
	if _run_over:
		return
	_run_over = true
	_raid_fail_ui("died")
	if Net.online:
		if Net.is_host():
			Net.rpc("rpc_raid_failed")
		else:
			Net.rpc("rpc_report_player_died")
	_end_raid()

func net_raid_failed() -> void:
	## Received: a teammate died — the whole team loses the run
	if _run_over:
		return
	_run_over = true
	_raid_fail_ui("teammate")
	_end_raid()

func _raid_fail_ui(cause: String) -> void:
	_run_loot_lost()
	Sfx.raid_failed()
	hud.set_extraction(false, 0.0)
	if cause == "teammate":
		hud.show_message("A TEAMMATE DIED — RAID FAILED", 4.0)
	else:
		hud.show_message(I18n.t("died"), 4.0)
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

func _run_loot_lost() -> void:
	pass  # dying simply discards run_loot; stash stays untouched
