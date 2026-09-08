extends Node3D
## 中式旧物废料线第三批探针: 验证 4 件新 GLB 在 Godot 中能正常加载 + 渲染。
##
## 坑9: -s 的 _init() 节点不在树, 用 _ready() 场景化.
## 坑15: 不跑 --check-only, 用场景化探针 + headless 主场景抓真错.
## 运行: godot --headless --path . res://tools/godot/probe_chinese_relics3.tscn

const NEW_RELICS := [
	"res://assets/static/vendor/chinese/abacus.glb",
	"res://assets/static/vendor/chinese/kerosene_lamp.glb",
	"res://assets/static/vendor/chinese/enamel_spittoon.glb",
	"res://assets/static/vendor/chinese/gramophone.glb",
]

func _ready() -> void:
	# 1) 资源存在 + 可加载
	var loaded := 0
	for path in NEW_RELICS:
		if not ResourceLoader.exists(path):
			print("ZHR3_MISSING ", path)
			continue
		var ps := load(path) as PackedScene
		if ps == null:
			print("ZHR3_BAD_PCK ", path)
			continue
		var inst := ps.instantiate()
		if not (inst is Node3D):
			print("ZHR3_NOT_NODE3D ", path)
			continue
		inst.name = "ZHR3_" + path.get_file().get_basename()
		add_child(inst)
		var meshes: Array[MeshInstance3D] = []
		for c in inst.find_children("*", "MeshInstance3D", true, false):
			meshes.append(c as MeshInstance3D)
		if meshes.is_empty():
			print("ZHR3_NO_MESH ", path)
			continue
		var total_verts := 0
		for m in meshes:
			if m.mesh:
				total_verts += m.mesh.get_faces().size() / 3
		print("ZHR3_OK ", path.get_file(), " meshes=", meshes.size(),
				" approx_tris=", total_verts)
		loaded += 1

	# 2) 验证 loot_box.gd 的 RELIC_MODELS 池已含全部 12 件 (8 旧 + 4 新)
	var lb_script := load("res://game/scripts/loot_box.gd")
	var pool: Array = lb_script.RELIC_MODELS
	print("ZHR3_POOL size=", pool.size())
	var new_in_pool := 0
	for p in NEW_RELICS:
		if pool.has(p):
			new_in_pool += 1
	print("ZHR3_POOL_NEW=", new_in_pool, "/", NEW_RELICS.size())

	var ok := (loaded == NEW_RELICS.size()) and (new_in_pool == NEW_RELICS.size())
	print("ZHR3_PROBE ", "PASS" if ok else "FAIL")
	get_tree().quit()
