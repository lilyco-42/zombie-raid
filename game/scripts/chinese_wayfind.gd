extends Node
## 中式渐进 · 引路灯 —— 红灯笼作为设施(地牢)内部的导航路标。
##
## 只新增不删改: 独立于 dungeon_builder / chinese_facility, 由 world_raid 在
## 设施落位之后、导航烘焙之前调用。零建模, 全部复用 lantern_red.glb。
##
## 玩法价值: 程序化地牢最容易迷路。这里在"入口 -> 出口(回城传送门)"的最短
## 路径上每格挂一盏红灯笼, 且灯笼偏向"下一格"那一侧 —— 一串可跟随的灯链,
## 玩家不用看 HUD 就知道往哪走; 出口格挂三盏成簇 + 更亮的暖光, 远看即"出口"。
##
## 中式表达: 指路的是檐下灯笼, 不是西方式的箭头/荧光条。
##
## 安全: 灯笼吊在天花板下沿 (y = WALL_H - 0.86, 与 chinese_facility 同式),
## 永远在 2.6m 以上, 不挡寻路也不挡视线; 格心 6m 通道中间无实体。
## 已挂装饰灯笼 (ZF_lantern_red_*) 的格子不重复挂, 避免同格叠灯。

const ZH := "res://assets/static/vendor/chinese/"
const CELL := 6.0                 ## 与 dungeon_builder.CELL 一致
const WALL_H := 4.0               ## KayKit dungeon 墙高 (实测 4.0, 天花板 4.08)
const OFFSET := Vector3(120, 0, 120)  ## 与 dungeon_builder.OFFSET 一致
const HANG := "lantern_red"
const HANG_Y := WALL_H - 0.86     ## 灯笼顶沿 +0.86 -> 顶面贴天花板
const BIAS := 1.55                ## 灯链偏向下一格, 让"方向"可读
const EXIT_R := 1.15              ## 出口灯簇半径
const EXIT_N := 3                 ## 出口灯盏数

const DIRS: Array = [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]

var _cache := {}
var _seq := 0
var rng := RandomNumberGenerator.new()
## 入口 -> 出口 的格坐标链 (探针/调试核对用)
var path_cells: Array = []


func build(world: Node3D, dungeon: Dictionary, seed_value: int = -1) -> int:
	if seed_value < 0:
		rng.randomize()
	else:
		rng.seed = seed_value
	var cells: Array = dungeon.get("cells", [])
	if cells.is_empty():
		print("ZW_WAYFIND pieces=0 (no cells)")
		return 0
	var carved := {}
	for p in cells:
		carved[_key(p as Vector3)] = true
	var start := _key(dungeon.get("entrance", cells[0]) as Vector3)
	var goal := _key(dungeon.get("exit", cells[cells.size() - 1]) as Vector3)
	if not carved.has(start) or not carved.has(goal):
		print("ZW_WAYFIND pieces=0 (endpoint not carved)")
		return 0
	var path: Array = _bfs(carved, start, goal)
	if path.size() < 2:
		print("ZW_WAYFIND pieces=0 (no path)")
		return 0
	path_cells = path
	# 设施篇已经随机挂过的装饰灯笼 -> 同格不叠第二盏
	var busy := _existing_lanterns(world)
	var placed := 0
	for i in path.size():
		var c: Vector2i = path[i]
		if i < path.size() - 1:
			var nxt: Vector2i = path[i + 1]
			var dirv := Vector3(float(nxt.x - c.x), 0.0, float(nxt.y - c.y))
			placed += _hang(world, _cell_world(c) + dirv * BIAS, busy, false)
		else:
			placed += _exit_cluster(world, _cell_world(c), busy)
	print("ZW_WAYFIND pieces=", placed, " path=", path.size())
	return placed


func _bfs(carved: Dictionary, start: Vector2i, goal: Vector2i) -> Array:
	var prev: Dictionary = {start: start}
	var queue: Array = [start]
	var head := 0
	while head < queue.size():
		var c: Vector2i = queue[head]
		head += 1
		if c == goal:
			break
		for d in DIRS:
			var n: Vector2i = c + (d as Vector2i)
			if not carved.has(n) or prev.has(n):
				continue
			prev[n] = c
			queue.append(n)
	if not prev.has(goal):
		return []
	var path: Array = []
	var cur: Vector2i = goal
	while cur != start:
		path.append(cur)
		cur = prev[cur] as Vector2i
	path.append(start)
	path.reverse()
	return path


func _existing_lanterns(world: Node3D) -> Array:
	## chinese_facility 挂过的装饰灯笼 (ZF_lantern_red_*) 的世界坐标
	var out: Array = []
	for c in world.get_children():
		if not String(c.name).begins_with("ZF_" + HANG):
			continue
		if c is Node3D:
			out.append((c as Node3D).global_position)
	return out


func _exit_cluster(world: Node3D, center: Vector3, busy: Array) -> int:
	## 出口: 三盏成簇 + 更亮暖光, 作为"这边能出去"的远距锚点
	var n := 0
	var base := rng.randf() * TAU
	for i in EXIT_N:
		var a := base + TAU * float(i) / float(EXIT_N)
		var pos := center + Vector3(cos(a) * EXIT_R, 0.0, sin(a) * EXIT_R)
		n += _hang(world, pos, busy, true)
	return n


func _hang(world: Node3D, pos: Vector3, busy: Array, is_exit: bool) -> int:
	pos.y = HANG_Y   # 统一吊在天花板下沿, 调用方只给 XZ
	for b in busy:
		if (b as Vector3).distance_to(pos) < 1.6:
			return 0
	var inst := _spawn(world, HANG, pos, Vector3(0.0, rng.randf() * TAU, 0.0))
	if inst == null:
		return 0
	var light := OmniLight3D.new()
	light.name = "ZW_LanternLight"
	light.light_color = Color(1.0, 0.46, 0.24) if is_exit else Color(1.0, 0.52, 0.32)
	light.light_energy = 3.0 if is_exit else 1.8
	light.omni_range = 9.0 if is_exit else 6.5
	light.shadow_enabled = false
	inst.add_child(light)
	return 1


func _key(p: Vector3) -> Vector2i:
	return Vector2i(int(round((p.x - OFFSET.x) / CELL - 0.5)),
		int(round((p.z - OFFSET.z) / CELL - 0.5)))


func _cell_world(c: Vector2i) -> Vector3:
	return OFFSET + Vector3((c.x + 0.5) * CELL, 0.0, (c.y + 0.5) * CELL)


func _spawn(world: Node3D, model: String, pos: Vector3, rot: Vector3) -> Node3D:
	var path := ZH + model + ".glb"
	if not ResourceLoader.exists(path):
		push_warning("ZW missing model: " + path)
		return null
	if not _cache.has(model):
		_cache[model] = load(path)
	var scene: PackedScene = _cache[model]
	if scene == null:
		return null
	var inst: Node3D = scene.instantiate()
	_seq += 1
	inst.name = "ZW_%s_%03d" % [model, _seq]
	world.add_child(inst)
	inst.global_position = pos
	inst.rotation = rot
	return inst
