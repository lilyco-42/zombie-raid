extends Node3D
## Raid map orchestrator: builds the city, bakes the navmesh,
## seeds zombie spawn points, then hands over to the raid manager.

const CityBuilderScript := preload("res://game/scripts/city_builder.gd")
const AvatarScript := preload("res://game/scripts/player_avatar.gd")
const DungeonBuilderScript := preload("res://game/scripts/dungeon_builder.gd")
const TouchControlsScript := preload("res://game/scripts/touch_controls.gd")
const ShopMenuScript := preload("res://game/scripts/shop_menu.gd")
const GreatWallScript := preload("res://game/scripts/greatwall_perimeter.gd")
const ChineseDistrictScript := preload("res://game/scripts/chinese_district.gd")
const PointerLockScript := preload("res://game/scripts/pointer_lock.gd")
const TutorialScript := preload("res://game/scripts/tutorial_overlay.gd")

@onready var player: CharacterBody3D = $PlayerInstance
@onready var manager: Node = $Manager
var shop: CanvasLayer
var pointer_lock: Node
var _waiting_for_seed := false
var _wait_overlay: CanvasLayer

func _ready() -> void:
	Net.world = self
	if not _sync_net_seed():
		return  # unseeded client: hold until the host's seed arrives
	_build_world()

func _sync_net_seed() -> bool:
	## Deterministic world: everyone builds from the host's seed.
	## Returns false when a client must wait for its seed (shows an overlay).
	if not Net.online:
		return true
	if Net.is_host():
		Net.raid_seed = randi()
		seed(Net.raid_seed)
		Net.rpc("rpc_seed", Net.raid_seed, 0.0)
		return true
	if Net.pending_seed >= 0:
		Net.raid_seed = Net.pending_seed
		Net.pending_seed = -1
		seed(Net.raid_seed)
		return true
	_waiting_for_seed = true
	_show_wait_overlay()
	return false

func _show_wait_overlay() -> void:
	_wait_overlay = CanvasLayer.new()
	_wait_overlay.layer = 95
	var lbl := Label.new()
	lbl.text = "WAITING FOR HOST — syncing world seed..."
	lbl.set_anchors_preset(Control.PRESET_CENTER)
	lbl.position = Vector2(0, -40)
	_wait_overlay.add_child(lbl)
	add_child(_wait_overlay)

func _build_world() -> void:
	player.add_to_group("player")
	var avatar: Node3D = AvatarScript.new()
	avatar.name = "PlayerAvatar"
	player.add_child(avatar)
	if _wants_touch_controls():
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

	# 中式渐变第一层: 城市外围长城 rampart (必须在导航烘焙前落位)
	var greatwall := Node.new()
	greatwall.name = "GreatWall"
	greatwall.set_script(GreatWallScript)
	add_child(greatwall)
	greatwall.build(self)

	# 中式渐进 · 城内篇: 越靠近城心, 中式密度与体量越高
	var district := Node.new()
	district.name = "ChineseDistrict"
	district.set_script(ChineseDistrictScript)
	add_child(district)
	district.build(self)

	# 鼠标锁定守卫: 先关着, 新手引导关闭后再启用
	pointer_lock = Node.new()
	pointer_lock.name = "PointerLock"
	pointer_lock.set_script(PointerLockScript)
	add_child(pointer_lock)

	var dungeon_builder := Node.new()
	dungeon_builder.name = "DungeonBuilder"
	dungeon_builder.set_script(DungeonBuilderScript)
	add_child(dungeon_builder)
	var dungeon: Dictionary = dungeon_builder.build(self, randi())

	_seed_spawn_points(info["block_centers"])
	_setup_navigation()
	manager.setup(self, player, info["block_centers"], dungeon)
	Net.spawn_remote_avatars()
	if Net.online and not Net.is_host():
		# Late join: the raid is already running on the host
		manager.elapsed = Net.pending_elapsed
		Net.pending_elapsed = 0.0
	if Net.online and not Net.is_host() and manager.elapsed > 1.0:
		_apply_upgrades()  # raid in progress: skip the shop, go straight in
	else:
		_open_shop()
	var lobby := CanvasLayer.new()
	lobby.name = "NetLobby"
	lobby.set_script(load("res://game/scripts/net_lobby.gd"))
	add_child(lobby)

func _process(_delta: float) -> void:
	if _waiting_for_seed:
		if not Net.online:
			# Host gave up while we waited: play solo
			_waiting_for_seed = false
			if _wait_overlay:
				_wait_overlay.queue_free()
				_wait_overlay = null
			_build_world()
		elif Net.pending_seed >= 0:
			get_tree().reload_current_scene()
		return
	if Net.online and player != null:
		var hv := Vector3(player.velocity.x, 0, player.velocity.z)
		Net.push_player_state(
			player.global_position, player.global_rotation.y, hv.length(),
			player.is_on_floor(), bool(player.get("crouched")))

func _open_shop() -> void:
	## Between-raid shop: world is built and paused behind it; DEPLOY resumes.
	shop = CanvasLayer.new()
	shop.name = "ShopMenu"
	shop.set_script(ShopMenuScript)
	add_child(shop)
	shop.deployed.connect(_apply_upgrades)
	shop.open()

func _apply_upgrades() -> void:
	## Permanent upgrades bought in the shop, applied to this raid's player.
	var hp_lvl: int = Stash.upgrade_level("health")
	var speed_lvl: int = Stash.upgrade_level("speed")
	var loot_lvl: int = Stash.upgrade_level("loot")
	if hp_lvl > 0:
		player.max_health = 100.0 + 25.0 * hp_lvl
		player.current_health = player.max_health
	if speed_lvl > 0:
		manager.speed_bonus = 0.06 * speed_lvl
	if loot_lvl > 0:
		manager.loot_bonus = 1.0 + 0.12 * loot_lvl
	if Stash.upgrade_level("medkit") > 0:
		# A free medkit box lands at your feet — save it for deep in the raid
		manager._spawn_medkit(player.global_position + Vector3(1.5, 0, 0))
	if Net.online:
		Net.raid_active = true
		if Net.is_host():
			Net.rpc("rpc_raid_started")
	_show_tutorial()

func _show_tutorial() -> void:
	## 新手引导: 每局开场显示一次, 关闭后才交出鼠标锁 (引导需要光标看键位表)。
	var tutorial: CanvasLayer = TutorialScript.new()
	tutorial.name = "Tutorial"
	add_child(tutorial)
	tutorial.dismissed.connect(_enable_pointer_lock)

func _enable_pointer_lock() -> void:
	if pointer_lock:
		pointer_lock.call("set_enabled", true)

func _wants_touch_controls() -> bool:
	## 触屏笔记本/桌面浏览器的 navigator 也会报"有触摸屏"(maxTouchPoints>0),
	## 但它们有键鼠。只有"触摸 + 无精细指针"的移动端才启用虚拟按钮。
	if not DisplayServer.is_touchscreen_available():
		return false
	if OS.has_feature("web"):
		var fine = JavaScriptBridge.eval("window.matchMedia('(pointer: fine)').matches", true)
		if fine == null:
			return false  # JS 不可用 -> 按桌面处理
		return String(fine) != "true"
	return OS.has_feature("mobile")


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
