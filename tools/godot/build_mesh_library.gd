extends SceneTree
## 把收编的地牢/后室件打成 GridMap MeshLibrary。
## 产出 assets/maps/gridmap_facility.tres (4m 网格, 三磁贴碰撞, 按 kit 去重材质)。
## 网格锚点约定用射线探针实测 (格子中心 or 角), 不做假设。
## 运行: godot --headless --path . -s res://tools/godot/build_mesh_library.gd

const OUT := "res://assets/maps/gridmap_facility.tres"
const CELL := 4.0

const DGN := "res://assets/static/vendor/dungeon/"
const BK := "res://assets/static/vendor/backrooms/"

# [item_name, glb_path, kit]
var ITEMS := [
	# --- 地牢 (SCP/LC 段, 暗石冷调) ---
	["dgn_wall", DGN + "wall.glb", "dgn"],
	["dgn_wall_arched", DGN + "wall_arched.glb", "dgn"],
	["dgn_wall_broken", DGN + "wall_broken.glb", "dgn"],
	["dgn_wall_corner", DGN + "wall_corner.glb", "dgn"],
	["dgn_wall_doorway", DGN + "wall_doorway.glb", "dgn"],
	["dgn_wall_gated", DGN + "wall_gated.glb", "dgn"],
	["dgn_wall_window", DGN + "wall_window_closed.glb", "dgn"],
	["dgn_pillar", DGN + "pillar.glb", "dgn"],
	["dgn_column", DGN + "column.glb", "dgn"],
	["dgn_floor", DGN + "floor_tile_large.glb", "dgn"],
	["dgn_floor_dirt", DGN + "floor_dirt_large.glb", "dgn"],
	["dgn_grate_4x2", DGN + "floor_tile_grate.glb", "dgn"],
	["dgn_stairs", DGN + "stairs.glb", "dgn"],
	["dgn_stairs_narrow", DGN + "stairs_narrow.glb", "dgn"],
	["dgn_torch", DGN + "torch_lit.glb", "dgn"],
	["dgn_candle", DGN + "candle_triple.glb", "dgn"],
	["dgn_barrel", DGN + "barrel_large.glb", "dgn"],
	["dgn_crates", DGN + "crates_stacked.glb", "dgn"],
	["dgn_chest", DGN + "chest.glb", "dgn"],
	["dgn_table", DGN + "table_medium.glb", "dgn"],
	["dgn_chair", DGN + "chair.glb", "dgn"],
	["dgn_shelf", DGN + "shelf_large.glb", "dgn"],
	["dgn_rubble", DGN + "rubble_large.glb", "dgn"],
	["dgn_trunk", DGN + "trunk_medium_A.glb", "dgn"],
	# --- 后室 (芥末黄) ---
	["bk_wall", BK + "wall.glb", "bk"],
	["bk_wall_arched", BK + "wall_arched.glb", "bk"],
	["bk_wall_doorway", BK + "wall_doorway.glb", "bk"],
	["bk_pillar", BK + "pillar.glb", "bk"],
	["bk_column", BK + "column.glb", "bk"],
	["bk_carpet", BK + "floor_dirt_large.glb", "bk"],
]

var _mat_map := {}  # "kit/material_name" -> Material (同 kit 共享一份, 防 .tres 膨胀)


func _initialize() -> void:
	var ml := MeshLibrary.new()
	var id := 0
	for entry in ITEMS:
		var ps: PackedScene = load(entry[1])
		if ps == null:
			push_error("ML: load fail " + str(entry[1]))
			continue
		var inst: Node = ps.instantiate()
		var raw := _bake(inst, entry[2])
		var aabb := raw.get_aabb()
		# 顶点平移: bbox 底面中心 -> 原点
		var off := Vector3(
			-(aabb.position.x + aabb.size.x * 0.5),
			-aabb.position.y,
			-(aabb.position.z + aabb.size.z * 0.5))
		var final := _bake(inst, entry[2], off)
		var shape := final.create_trimesh_shape()
		ml.create_item(id)
		ml.set_item_name(id, entry[0])
		ml.set_item_mesh(id, final)
		ml.set_item_shapes(id, [shape, Transform3D()])
		print("ML[%d] %s aabb=%s" % [id, entry[0], aabb.size])
		id += 1
		inst.free()
	print("ML items=", ml.get_item_list().size())
	var err := ResourceSaver.save(ml, OUT)
	print("ML saved err=", err, " -> ", OUT)
	# 注意: -s 脚本模式下 await physics_frame 永不触发 (会挂死),
	# 网格锚点探针放在 tests/test_gridmap.gd (场景化, process_frame 可用)
	quit(0)


func _ray_down(gm: GridMap, from: Vector3) -> Vector3:
	var space := gm.get_world_3d().direct_space_state
	var q := PhysicsRayQueryParameters3D.create(from, from + Vector3(0, -60, 0))
	var res := space.intersect_ray(q)
	return res.position if res.has("position") else Vector3.INF


## 合并 inst 下所有 MeshInstance3D -> 单个 ArrayMesh; off 可选顶点平移
func _bake(inst: Node, kit: String, off := Vector3.ZERO) -> ArrayMesh:
	var out := ArrayMesh.new()
	_collect(inst, Transform3D(), out, kit, off)
	return out


func _collect(n: Node, xf: Transform3D, out: ArrayMesh, kit: String, off: Vector3) -> void:
	for c in n.get_children():
		var cxf := xf
		if c is Node3D:
			cxf = xf * (c as Node3D).transform
		if c is MeshInstance3D and (c as MeshInstance3D).mesh != null:
			_append(out, (c as MeshInstance3D).mesh, cxf, kit, off)
		_collect(c, cxf, out, kit, off)


func _append(out: ArrayMesh, mesh: Mesh, xf: Transform3D, kit: String, off: Vector3) -> void:
	for s in mesh.get_surface_count():
		var arrays: Array = mesh.surface_get_arrays(s)
		if arrays[Mesh.ARRAY_VERTEX] == null:
			continue
		var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		for i in verts.size():
			verts[i] = xf * verts[i] + off
		arrays[Mesh.ARRAY_VERTEX] = verts
		var norms = arrays[Mesh.ARRAY_NORMAL]
		if norms != null:
			var nrm: PackedVector3Array = norms
			for i in nrm.size():
				nrm[i] = xf.basis * nrm[i]
			arrays[Mesh.ARRAY_NORMAL] = nrm
		out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		var mat: Material = mesh.surface_get_material(s)
		out.surface_set_material(out.get_surface_count() - 1, _canonical(kit, mat))


## 同 kit 同名材质共享一份, 避免每件各嵌一份纹理导致 .tres 膨胀
func _canonical(kit: String, mat: Material) -> Material:
	if mat == null:
		return null
	var key := kit + "/" + mat.resource_name
	if not _mat_map.has(key):
		_mat_map[key] = mat
	return _mat_map[key]
