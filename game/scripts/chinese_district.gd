extends Node
## 中式渐进 · 城内篇 —— 越靠近城心, 中式密度与体量越高。
##
## 只新增不删改: 独立于 city_builder, 由 world_raid 在导航烘焙前调用。
## 点位是算出来的安全位 (避开车道带与建筑占地):
##   · 车道占用 |x|/|z| < 3 与 |x|/|z| - 18| < 3 的带状区域
##   · 建筑占每个 block 中心 (+-9 / +-24) 半径 ~5
##   => 取 (±4.5, ±4.5) r≈6.4 / (±4.5, ±13.5) 与 (±13.5, ±4.5) r≈14.2 / (±13.5, ±13.5) r≈19.1
## 三档: 最内 4 点放大件地标 (塔/华表/铜钟/井台), 中圈 8 点放中件, 外圈 4 点放小件。

const ZH := "res://assets/static/vendor/chinese/"

## 最内圈 (r≈6.4): 城心大地标, 一进内城就看见
const INNER := ["brick_pagoda", "huabiao", "bronze_bell", "well"]
## 中圈 (r≈14.2): 园宅级中件
const MID := ["moon_gate", "stone_lion", "incense_burner", "screen_wall",
			  "taihu_rock", "stele", "stone_lantern", "stone_censer"]
## 外圈 (r≈19.1): 街头小件, 密度最低 —— 中式是"渗进来"的
const OUTER := ["water_vat", "stone_bench", "hitching_post", "mendun"]

const SPOT_INNER := [
	Vector3(4.5, 0.0, 4.5), Vector3(-4.5, 0.0, 4.5),
	Vector3(4.5, 0.0, -4.5), Vector3(-4.5, 0.0, -4.5),
]
const SPOT_MID := [
	Vector3(4.5, 0.0, 13.5), Vector3(-4.5, 0.0, 13.5),
	Vector3(4.5, 0.0, -13.5), Vector3(-4.5, 0.0, -13.5),
	Vector3(13.5, 0.0, 4.5), Vector3(-13.5, 0.0, 4.5),
	Vector3(13.5, 0.0, -4.5), Vector3(-13.5, 0.0, -4.5),
]
const SPOT_OUTER := [
	Vector3(13.5, 0.0, 13.5), Vector3(-13.5, 0.0, 13.5),
	Vector3(13.5, 0.0, -13.5), Vector3(-13.5, 0.0, -13.5),
]

var _cache := {}
var _seq := 0


func build(world: Node3D) -> void:
	_ring(world, SPOT_INNER, INNER)
	_ring(world, SPOT_MID, MID)
	_ring(world, SPOT_OUTER, OUTER)


func _ring(world: Node3D, spots: Array, models: Array) -> void:
	for i in spots.size():
		var model: String = models[i % models.size()]
		_place(world, model, spots[i], randf() * TAU)


func _model(name: String) -> PackedScene:
	if not _cache.has(name):
		var path := ZH + name + ".glb"
		if ResourceLoader.exists(path):
			_cache[name] = load(path)
		else:
			push_warning("Chinese model missing: " + path)
			_cache[name] = null
	return _cache[name]


func _place(world: Node3D, name: String, pos: Vector3, yaw: float) -> Node3D:
	var scene := _model(name)
	if scene == null:
		return null
	var inst: Node3D = scene.instantiate()
	_seq += 1
	inst.name = "ZH_%s_%02d" % [name, _seq]
	world.add_child(inst)
	inst.global_position = pos
	inst.rotation.y = yaw
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		mi.create_trimesh_collision()
	return inst
