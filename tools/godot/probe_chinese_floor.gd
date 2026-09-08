extends Node3D
## 青砖铺地探针 (场景化, 见坑9: -s 的 SceneTree 脚本里节点不在树上)。
## 运行: godot --headless --path . res://tools/godot/probe_chinese_floor.tscn
##
## 断言: ① 落位数 == 2 x 开凿格数 (地面+顶面) 且 > 0
##       ② 地面砖顶面 = 0.11 (高出旧砖顶面 0.08, 不共面)
##          顶面砖底面 = 4.00 (低于旧顶棚底面 4.03, 不共面)
##       ③ 每块砖中心都落在某个开凿格心上 (XZ 完全重合)
##       ④ 覆盖: 每个开凿格恰好 1 地面 + 1 顶面, 无遗漏无重复
## 产出: assets/_previews/zh_floor_map.png (俯视覆盖图)

const CELL := 6.0
const OFFSET := Vector3(120, 0, 120)
const GRID := 10
const FLOOR_TOP := 0.11
const CEIL_BOTTOM := 4.0


func _ready() -> void:
	var db := Node.new()
	db.name = "DungeonBuilder"
	db.set_script(load("res://game/scripts/dungeon_builder.gd"))
	add_child(db)
	var dungeon: Dictionary = db.build(self, 20260908)

	var zf := Node.new()
	zf.name = "ChineseFloor"
	zf.set_script(load("res://game/scripts/chinese_floor.gd"))
	add_child(zf)
	var placed: int = zf.build(self, dungeon)

	var cells: Array = dungeon["cells"]
	var tiles: Array = []
	for c in get_children():
		if String(c.name).begins_with("ZF_brick"):
			tiles.append(c as Node3D)

	var ok := (tiles.size() == placed) and (placed == cells.size() * 2) and placed > 0
	var bad_y := 0
	var floor_per_cell := {}
	var ceil_per_cell := {}
	for t in tiles:
		var tn := t as Node3D
		var p := tn.global_position
		# 地面: rotation 零 -> 占 [y, y+0.06]; 顶面: 翻转 -> 占 [y-0.06, y]
		var flipped := absf(tn.rotation.x) > 1.0
		var top := p.y + 0.06 if not flipped else p.y
		var bottom := p.y if not flipped else p.y - 0.06
		if flipped:
			if absf(bottom - CEIL_BOTTOM) > 0.01:
				bad_y += 1
			ceil_per_cell[_ckey(p)] = ceil_per_cell.get(_ckey(p), 0) + 1
		else:
			if absf(top - FLOOR_TOP) > 0.01:
				bad_y += 1
			floor_per_cell[_ckey(p)] = floor_per_cell.get(_ckey(p), 0) + 1
	if bad_y > 0:
		ok = false

	# 覆盖: 每个开凿格恰好 1 + 1
	var missing := 0
	var dup := 0
	for p in cells:
		var k := _ckey(p as Vector3)
		var f: int = floor_per_cell.get(k, 0)
		var cc: int = ceil_per_cell.get(k, 0)
		if f != 1 or cc != 1:
			if f + cc == 0:
				missing += 1
			else:
				dup += 1
	if missing > 0 or dup > 0:
		ok = false

	print("ZF_PROBE returned=", placed, " nodes=", tiles.size(),
		" cells=", cells.size(), " bad_y=", bad_y,
		" missing=", missing, " dup=", dup)
	_write_map(cells, floor_per_cell)
	print("ZF_PROBE " + ("PASS" if ok else "FAIL"))
	get_tree().quit()


func _ckey(p: Vector3) -> Vector2i:
	return Vector2i(int(round((p.x - OFFSET.x) / CELL - 0.5)),
		int(round((p.z - OFFSET.z) / CELL - 0.5)))


func _write_map(cells: Array, floor_per_cell: Dictionary) -> void:
	var px := 40
	var m := 12
	var n := GRID * px + m * 2
	var img := Image.create(n, n, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.05, 0.05, 0.07))
	for p in cells:
		var c := _ckey(p as Vector3)
		var done: int = floor_per_cell.get(c, 0)
		var col := Color(0.30, 0.33, 0.34) if done == 1 else Color(0.70, 0.15, 0.12)
		_fill(img, m + c.x * px + 2, m + c.y * px + 2, px - 4, px - 4, col)
	var out := ProjectSettings.globalize_path("res://assets/_previews/zh_floor_map.png")
	DirAccess.make_dir_recursive_absolute(out.get_base_dir())
	var err := img.save_png(out)
	print("ZF_MAP_PNG ", out, " err=", err)


func _fill(img: Image, x: int, y: int, w: int, h: int, col: Color) -> void:
	var r := Rect2i(x, y, w, h).intersection(Rect2i(0, 0, img.get_width(), img.get_height()))
	if r.size.x <= 0 or r.size.y <= 0:
		return
	img.fill_rect(r, col)
