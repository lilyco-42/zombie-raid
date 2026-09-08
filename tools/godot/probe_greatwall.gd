extends Node3D
## 长城外围落位探针 (场景化, 见坑9: -s SceneTree 脚本里节点不在树上)。
## 运行: godot --headless --path . res://tools/godot/probe_greatwall.tscn
## 预期: 32 段墙 (8 槽 x 4 边) + 9 障墙 = 41

func _ready() -> void:
	var gw_script = load("res://game/scripts/greatwall_perimeter.gd")
	var gw := Node.new()
	gw.name = "GreatWall"
	gw.set_script(gw_script)
	add_child(gw)
	gw.build(self)

	var district_script = load("res://game/scripts/chinese_district.gd")
	var district := Node.new()
	district.name = "ChineseDistrictProbe"
	district.set_script(district_script)
	add_child(district)
	district.build(self)

	var gw_count := 0
	var zh_count := 0
	for c in get_children():
		var n := String(c.name)
		if n.begins_with("GW_"):
			gw_count += 1
		elif n.begins_with("ZH_"):
			zh_count += 1
	print("GW_PROBE pieces=", gw_count)
	print("ZH_PROBE pieces=", zh_count)
	var ok := (gw_count == 41 and zh_count == 16)
	print("ZH_PROBE " + ("PASS" if ok else "CHECK"))
	get_tree().quit()
