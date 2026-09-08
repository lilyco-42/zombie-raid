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

	var pieces := 0
	var tally := {}
	for c in get_children():
		if String(c.name).begins_with("GW_"):
			pieces += 1
			tally[String(c.name)] = int(tally.get(String(c.name), 0)) + 1
	print("GW_PROBE pieces=", pieces)
	for k in tally.keys():
		print("  ", k, " x", tally[k])
	print("GW_PROBE " + ("PASS" if pieces == 41 else "CHECK"))
	get_tree().quit()
