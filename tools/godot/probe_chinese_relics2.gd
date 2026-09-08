extends Node3D
## 中式旧物废料线第二批探针: 验证 4 件新 GLB 在 Godot 中能正常加载 + 渲染。
##
## 坑9: -s 的 _init() 节点不在树, 用 _ready() 场景化.
## 坑14: 不是验证构建器, 是验证资源管线; 跑通即可 commit.
## 运行: godot --headless --path . res://tools/godot/probe_chinese_relics2.tscn

const NEW_RELICS := [
	"res://assets/static/vendor/chinese/old_letter.glb",
	"res://assets/static/vendor/chinese/work_badge.glb",
	"res://assets/static/vendor/chinese/half_jade.glb",
	"res://assets/static/vendor/chinese/old_radio.glb",
]

func _ready() -> void:
	# 1) 资源存在 + 可加载
	var loaded := 0
	for path in NEW_RELICS:
		if not ResourceLoader.exists(path):
			print("ZHR2_MISSING ", path)
			continue
		var ps := load(path) as PackedScene
		if ps == null:
			print("ZHR2_BAD_PCK ", path)
			continue
		var inst := ps.instantiate()
		# 任何 GLB 的根必须是 Node3D, 至少含一个 MeshInstance3D
		if not (inst is Node3D):
			print("ZHR2_NOT_NODE3D ", path)
			continue
		inst.name = "ZHR2_" + path.get_file().get_basename()
		add_child(inst)
		var meshes: Array[MeshInstance3D] = []
		inst.find_children("*", "MeshInstance3D", true, false)
		for c in inst.find_children("*", "MeshInstance3D", true, false):
			meshes.append(c as MeshInstance3D)
		if meshes.is_empty():
			print("ZHR2_NO_MESH ", path)
			continue
		var total_verts := 0
		for m in meshes:
			if m.mesh:
				total_verts += m.mesh.get_faces().size() / 3
		print("ZHR2_OK ", path.get_file(), " meshes=", meshes.size(),
				" approx_tris=", total_verts)
		loaded += 1

	# 2) 验证 loot_box.gd 的 RELIC_MODELS 池已含全部 8 件 (4 旧 + 4 新)
	var lb_script := load("res://game/scripts/loot_box.gd")
	var pool: Array = lb_script.RELIC_MODELS
	print("ZHR2_POOL size=", pool.size())
	var new_in_pool := 0
	for p in NEW_RELICS:
		if pool.has(p):
			new_in_pool += 1
	print("ZHR2_POOL_NEW=", new_in_pool, "/", NEW_RELICS.size())

	var ok := (loaded == NEW_RELICS.size()) and (new_in_pool == NEW_RELICS.size())
	print("ZHR2_PROBE ", "PASS" if ok else "FAIL")
	get_tree().quit()
