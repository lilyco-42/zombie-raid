extends Node
## 中式渐进 · 设施篇 —— 越深入越中式, 补齐最深一层 (设施内部) 的中式落位。
##
## 只新增不删改: 独立于 dungeon_builder, 由 world_raid 在导航烘焙前调用,
## 沿用 dungeon 的网格 (6m 一格, 墙高 3.5m), 只在已开凿的格子里加装饰。
##
## 全部复用 assets/static/vendor/chinese/ 已有件 (零建模):
##   · 卷帘门 roller_door       3.94 x 3.99 x 0.52  (贴封闭墙面, 缩 0.85 塞进层高)
##   · 标语牌 slogan_*          4.04 x 1.97 x 0.46  (贴墙, 抬到 y=1.15)
##   · 红灯笼 lantern_red       0.63 x 1.09 x 0.60  (吊在天花板, 自带暖光)
##   · 八仙桌 ba_xian_table     1.02 x 0.85 x 1.02  + 方凳 stool 环绕
##   · 祭祀角 offering_table + incense_burner + paper_ash (死胡同锚点)
##   · 靠角大件 water_vat / stone_mill
##
## 安全: 大件一律靠格角 (±1.7~2.1m) 摆放, 6m 通道中间永远留空, 不挡寻路。
## 朝向: 贴墙件薄面在 Z, 正面 +Z 朝房间内 —— yaw = atan2(-dir.x, -dir.z)。

const ZH := "res://assets/static/vendor/chinese/"
const CELL := 6.0        ## 与 dungeon_builder.CELL 一致
const WALL_H := 4.0      ## KayKit dungeon 墙高 (实测 4.0, 天花板 4.08)
const WALL_FACE := 2.27  ## 墙内表面 2.5 - 半厚, 贴墙件的中心到格心的距离

const WALL_BOARDS := ["slogan_safety", "slogan_tunnel"]
const DOOR := "roller_door"
const HANG := "lantern_red"
const CORNER := ["water_vat", "stone_mill"]
const ALTAR_TABLE := "offering_table"
const ALTAR_ON := "incense_burner"
const ALTAR_FRONT := "paper_ash"
const TABLE := "ba_xian_table"
const STOOL := "stool"

const DIRS: Array = [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]

var _cache := {}
var _seq := 0
var rng := RandomNumberGenerator.new()


func build(world: Node3D, dungeon: Dictionary, seed_value: int = -1) -> int:
	if seed_value < 0:
		rng.randomize()
	else:
		rng.seed = seed_value
	var cells: Array = dungeon.get("cells", [])
	if cells.is_empty():
		print("ZF_FACILITY pieces=0 (no cells)")
		return 0
	var carved := {}
	for p in cells:
		carved[_key(p as Vector3)] = true
	var placed := 0
	for p in cells:
		placed += _decorate_cell(world, p as Vector3, carved)
	print("ZF_FACILITY pieces=", placed)
	return placed


func _key(p: Vector3) -> Vector2i:
	return Vector2i(int(round(p.x / CELL)), int(round(p.z / CELL)))


func _decorate_cell(world: Node3D, center: Vector3, carved: Dictionary) -> int:
	var k := _key(center)
	var closed: Array = []
	var open_n := 0
	for d in DIRS:
		if carved.has(k + d):
			open_n += 1
		else:
			closed.append(d)
	if closed.is_empty():
		return 0
	var n := 0
	# 1) 贴墙: 标语牌 / 卷帘门
	if rng.randf() < 0.45:
		var d1: Vector2i = closed[rng.randi() % closed.size()]
		n += _mount_wall(world, center, d1,
			WALL_BOARDS[rng.randi() % WALL_BOARDS.size()], 1.15, 1.0)
	if rng.randf() < 0.20:
		var d2: Vector2i = closed[rng.randi() % closed.size()]
		n += _mount_wall(world, center, d2, DOOR, 0.0, 0.95)
	# 2) 红灯笼: 吊在天花板下沿, 带一盏暖光
	if rng.randf() < 0.32:
		n += _hang_lantern(world, center)
	# 3) 死胡同 -> 祭祀角 (设施最深处的中式锚点)
	if open_n <= 1 and rng.randf() < 0.8:
		n += _altar(world, center, closed)
	elif rng.randf() < 0.28:
		n += _table_set(world, center)
	# 4) 靠角大件
	if rng.randf() < 0.22:
		n += _corner_prop(world, center)
	return n


func _mount_wall(world: Node3D, center: Vector3, d: Vector2i, model: String,
		y: float, scl: float) -> int:
	var dirv := Vector3(float(d.x), 0.0, float(d.y))
	var pos := center + dirv * WALL_FACE
	pos.y = y
	var yaw := atan2(-dirv.x, -dirv.z)
	return 1 if _spawn(world, model, pos, Vector3(0.0, yaw, 0.0), false, scl) else 0


func _hang_lantern(world: Node3D, center: Vector3) -> int:
	var pos := center + Vector3(rng.randf_range(-1.3, 1.3), 0.0, rng.randf_range(-1.3, 1.3))
	pos.y = WALL_H - 0.86   # 灯笼 bbox 上沿 +0.86 -> 顶面贴天花板
	var inst := _spawn(world, HANG, pos, Vector3(0.0, rng.randf() * TAU, 0.0), false, 1.0)
	if inst == null:
		return 0
	var light := OmniLight3D.new()
	light.name = "ZF_LanternLight"
	light.light_color = Color(1.0, 0.52, 0.32)
	light.light_energy = 1.6
	light.omni_range = 6.5
	light.shadow_enabled = false
	inst.add_child(light)
	return 1


func _altar(world: Node3D, center: Vector3, closed: Array) -> int:
	var d: Vector2i = closed[rng.randi() % closed.size()]
	var dirv := Vector3(float(d.x), 0.0, float(d.y))
	var base := center + dirv * 1.45
	var yaw := atan2(-dirv.x, -dirv.z)
	var n := 0
	if _spawn(world, ALTAR_TABLE, base, Vector3(0.0, yaw, 0.0), true, 1.0):
		n += 1
	if _spawn(world, ALTAR_ON, base + Vector3(0.0, 0.98, 0.0),
			Vector3(0.0, yaw, 0.0), false, 1.0):
		n += 1
	if _spawn(world, ALTAR_FRONT, base - dirv * 0.85,
			Vector3(0.0, yaw, 0.0), false, 1.0):
		n += 1
	return n


func _table_set(world: Node3D, center: Vector3) -> int:
	var base := center + Vector3(rng.randf_range(-0.9, 0.9), 0.0,
		rng.randf_range(-0.9, 0.9))
	var yaw := rng.randf() * TAU
	var n := 0
	if _spawn(world, TABLE, base, Vector3(0.0, yaw, 0.0), true, 1.0):
		n += 1
	var cnt: int = 2 + rng.randi() % 3
	for i in cnt:
		var a := TAU * float(i) / float(cnt) + yaw
		var sp := base + Vector3(cos(a) * 0.95, 0.0, sin(a) * 0.95)
		if _spawn(world, STOOL, sp, Vector3(0.0, a + PI, 0.0), true, 1.0):
			n += 1
	return n


func _corner_prop(world: Node3D, center: Vector3) -> int:
	var sx := 1.0 if rng.randf() < 0.5 else -1.0
	var sz := 1.0 if rng.randf() < 0.5 else -1.0
	var pos := center + Vector3(sx * 1.55, 0.0, sz * 1.55)
	var model: String = CORNER[rng.randi() % CORNER.size()]
	return 1 if _spawn(world, model, pos, Vector3(0.0, rng.randf() * TAU, 0.0),
		true, 1.0) else 0


func _spawn(world: Node3D, model: String, pos: Vector3, rot: Vector3,
		with_collision: bool, scl: float) -> Node3D:
	var path := ZH + model + ".glb"
	if not ResourceLoader.exists(path):
		push_warning("ZF missing model: " + path)
		return null
	if not _cache.has(model):
		_cache[model] = load(path)
	var scene: PackedScene = _cache[model]
	if scene == null:
		return null
	var inst: Node3D = scene.instantiate()
	_seq += 1
	inst.name = "ZF_%s_%03d" % [model, _seq]
	world.add_child(inst)
	inst.global_position = pos
	inst.rotation = rot
	inst.scale = Vector3.ONE * scl
	if with_collision:
		for mi in inst.find_children("*", "MeshInstance3D", true, false):
			mi.create_trimesh_collision()
	return inst
