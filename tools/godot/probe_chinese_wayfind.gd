extends Node3D
## 中式引路灯探针 (场景化, 见坑9: -s 的 SceneTree 脚本里节点不在树上)。
## 运行: godot --headless --path . res://tools/godot/probe_chinese_wayfind.tscn
##
## 断言: ① 落位数 == 脚本返回值 且 > 0
##       ② 每盏灯笼吊在 y=3.14 (顶沿贴 4m 天花板)
##       ③ 每盏灯笼都在已开凿格内 (到最近格心 <= 1.6m, 即 BIAS 上限)
##       ④ 路径连续: 相邻格曼哈顿距离恒为 1, 且首尾 == 入口/出口
## 产出: ASCII 网格图 (日志) + assets/_previews/zh_wayfind_map.png (俯视目检)

const CELL := 6.0
const OFFSET := Vector3(120, 0, 120)
const GRID := 10
const HANG_Y := 4.0 - 0.86
const BIAS := 1.55

const DIRS: Array = [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]


func _ready() -> void:
	var db := Node.new()
	db.name = "DungeonBuilder"
	db.set_script(load("res://game/scripts/dungeon_builder.gd"))
	add_child(db)
	var dungeon: Dictionary = db.build(self, 20260908)

	var zf := Node.new()
	zf.name = "ChineseFacility"
	zf.set_script(load("res://game/scripts/chinese_facility.gd"))
	add_child(zf)
	zf.build(self, dungeon, 12345)   # 先挂装饰灯笼, 检验引路灯的同格避让

	var zw := Node.new()
	zw.name = "ChineseWayfind"
	zw.set_script(load("res://game/scripts/chinese_wayfind.gd"))
	add_child(zw)
	var placed: int = zw.build(self, dungeon, 777)

	# ---- 收集引路灯节点 ----
	var lanterns: Array = []
	for c in get_children():
		if String(c.name).begins_with("ZW_lantern_red"):
			lanterns.append(c as Node3D)
	var count := lanterns.size()

	# ---- 开凿格集合 + 格心 ----
	var carved := {}
	for p in dungeon["cells"]:
		carved[_key(p as Vector3)] = _cell(_key(p as Vector3))

	var ok := (count == placed) and (count > 0)
	var bad_y := 0
	var bad_cell := 0
	for l in lanterns:
		var ln := l as Node3D
		if absf(ln.global_position.y - HANG_Y) > 0.01:
			bad_y += 1
		var near := 1e9
		for k in carved:
			var ctr: Vector3 = carved[k]
			near = minf(near, Vector2(ln.global_position.x, ln.global_position.z)
				.distance_to(Vector2(ctr.x, ctr.z)))
		if near > BIAS + 0.05:
			bad_cell += 1
	if bad_y > 0:
		ok = false
	if bad_cell > 0:
		ok = false

	# ---- 路径连续性 ----
	var path: Array = zw.get("path_cells")
	var path_ok := path.size() >= 2
	for i in path.size() - 1:
		var a: Vector2i = path[i]
		var b: Vector2i = path[i + 1]
		if absi(a.x - b.x) + absi(a.y - b.y) != 1:
			path_ok = false
	var start_key := _key(dungeon["entrance"] as Vector3)
	var goal_key := _key(dungeon["exit"] as Vector3)
	if path.is_empty() or (path[0] as Vector2i) != start_key \
			or (path[path.size() - 1] as Vector2i) != goal_key:
		path_ok = false
	if not path_ok:
		ok = false

	print("ZW_PROBE returned=", placed, " nodes=", count,
		" bad_y=", bad_y, " out_of_cell=", bad_cell, " path=", path.size())
	_draw_ascii(carved, path, start_key, goal_key, lanterns)
	_write_map(carved, path, start_key, goal_key, lanterns)
	print("ZW_PROBE " + ("PASS" if ok else "FAIL"))
	get_tree().quit()


func _key(p: Vector3) -> Vector2i:
	return Vector2i(int(round((p.x - OFFSET.x) / CELL - 0.5)),
		int(round((p.z - OFFSET.z) / CELL - 0.5)))


func _cell(c: Vector2i) -> Vector3:
	return OFFSET + Vector3((c.x + 0.5) * CELL, 0.0, (c.y + 0.5) * CELL)


func _draw_ascii(carved: Dictionary, path: Array, start_key: Vector2i,
		goal_key: Vector2i, lanterns: Array) -> void:
	var on_path := {}
	for c in path:
		on_path[c as Vector2i] = true
	var lit := {}
	for l in lanterns:
		lit[_key((l as Node3D).global_position)] = true
	for y in GRID:
		var row := ""
		for x in GRID:
			var k := Vector2i(x, y)
			var ch := " "
			if carved.has(k):
				ch = "."
			if lit.has(k):
				ch = "o"
			if on_path.has(k):
				ch = "*"
			if k == start_key:
				ch = "E"
			if k == goal_key:
				ch = "X"
			row += ch
		print("ZW_MAP |" + row + "|")


func _write_map(carved: Dictionary, path: Array, start_key: Vector2i,
		goal_key: Vector2i, lanterns: Array) -> void:
	var px := 40
	var m := 12
	var n := GRID * px + m * 2
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.06, 0.06, 0.08))
	var on_path := {}
	for c in path:
		on_path[c as Vector2i] = true
	for k in carved:
		var c: Vector2i = k as Vector2i
		var col := Color(0.17, 0.17, 0.20)
		if on_path.has(c):
			col = Color(0.58, 0.13, 0.10)
		if c == start_key:
			col = Color(0.20, 0.80, 0.34)
		if c == goal_key:
			col = Color(1.0, 0.70, 0.24)
		_fill(img, m + c.x * px + 2, m + c.y * px + 2, px - 4, px - 4, col)
	for l in lanterns:
		var p: Vector3 = (l as Node3D).global_position
		var gx := (p.x - OFFSET.x) / CELL - 0.5
		var gz := (p.z - OFFSET.z) / CELL - 0.5
		var cx := int(round(m + (gx + 0.5) * px))
		var cy := int(round(m + (gz + 0.5) * px))
		_fill(img, cx - 5, cy - 5, 10, 10, Color(1.0, 0.55, 0.26))
	var out := ProjectSettings.globalize_path("res://assets/_previews/zh_wayfind_map.png")
	DirAccess.make_dir_recursive_absolute(out.get_base_dir())
	var err := img.save_png(out)
	print("ZW_MAP_PNG ", out, " err=", err)


func _fill(img: Image, x: int, y: int, w: int, h: int, col: Color) -> void:
	var r := Rect2i(x, y, w, h).intersection(Rect2i(0, 0, img.get_width(), img.get_height()))
	if r.size.x <= 0 or r.size.y <= 0:
		return
	img.fill_rect(r, col)
