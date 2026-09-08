extends Node3D
## 中式设施落位探针 (场景化, 见坑9: -s 的 SceneTree 脚本里节点不在树上)。
## 运行: godot --headless --path . res://tools/godot/probe_chinese_facility.tscn
## 固定种子 -> 结果可复现, 断言: 落位数 == 脚本返回值 且 > 0, 并打印构成。

func _ready() -> void:
	var db_script = load("res://game/scripts/dungeon_builder.gd")
	var db := Node.new()
	db.name = "DungeonBuilder"
	db.set_script(db_script)
	add_child(db)
	var dungeon: Dictionary = db.build(self, 20260908)

	var zf_script = load("res://game/scripts/chinese_facility.gd")
	var zf := Node.new()
	zf.name = "ChineseFacility"
	zf.set_script(zf_script)
	add_child(zf)
	var placed: int = zf.build(self, dungeon, 12345)

	var zf_count := 0
	var kinds := {}
	for c in get_children():
		var n := String(c.name)
		if not n.begins_with("ZF_"):
			continue
		zf_count += 1
		var model := n.substr(3, n.length() - 7)
		kinds[model] = int(kinds.get(model, 0)) + 1

	print("ZF_PROBE returned=", placed, " nodes=", zf_count)
	for k in kinds.keys():
		print("ZF_KIND ", k, "=", kinds[k])
	var ok := (zf_count == placed) and (zf_count > 0)
	print("ZF_PROBE " + ("PASS" if ok else "FAIL"))
	get_tree().quit()
