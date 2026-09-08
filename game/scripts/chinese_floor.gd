extends Node
## 中式渐进 · 青砖铺地 —— 设施(最深层)地面/顶面的砖石补缺。
##
## 只新增不删改: 独立于 dungeon_builder / chinese_facility, 由 world_raid 在
## 设施落位之后、导航烘焙之前调用。不动既有地砖, 用一块 6x6 青砖砖"盖"上去。
##
## 缺陷背景: dungeon_builder 按 CELL=6.0 开凿设施, 但 KayKit dungeon 的
## floor_tile_large / floor_wood_large_dark 实测只有 4.0 x 4.0, 每格一块 ->
## 每条格边界留 2m 宽空洞, 往下/往上看都是背景纯黑, 走廊像悬空栈道。
##
## 做法: 每个开凿格铺一块 brick_pave_6m.glb (6.0 x 0.06 x 6.0, 原点=底面中心)
##   地面  y=0.05  -> 占 [0.05, 0.11], 顶面比既有地砖顶面(0.08)高 3cm,
##                    完全盖住旧砖且避免共面 z-fighting
##   顶面  y=4.06  -> 翻转后占 [4.00, 4.06], 底面比既有顶棚底面(4.03)低 3cm,
##                    同样盖住且不共面
## 无碰撞(既有 FacilitySlab 提供行走碰撞)、无随机 -> 全端天然一致。
##
## 中式表达: 最深处换上青砖铺地(错缝/三档青灰), "越深入越中式"落到底。

const ZH := "res://assets/static/vendor/chinese/"
const TILE := "brick_pave_6m"
const FLOOR_Y := 0.05          ## 顶面 0.11, 高出旧砖顶面 0.08 三厘米
const WALL_H := 4.0            ## KayKit dungeon 墙高(实测), 与 wayfind/facility 一致
const CEIL_Y := WALL_H + 0.06  ## 翻转后底面 = 4.00, 低于旧顶棚底面 4.03

var _cache: PackedScene
var _seq := 0


func build(world: Node3D, dungeon: Dictionary) -> int:
	var cells: Array = dungeon.get("cells", [])
	if cells.is_empty():
		print("ZFLOOR pieces=0 (no cells)")
		return 0
	var path := ZH + TILE + ".glb"
	if not ResourceLoader.exists(path):
		push_warning("ZFLOOR missing model: " + path)
		return 0
	if _cache == null:
		_cache = load(path)
	var placed := 0
	for p in cells:
		var c: Vector3 = p as Vector3   # dungeon["cells"] 已是世界坐标 (y=0)
		placed += _lay(world, Vector3(c.x, FLOOR_Y, c.z), Vector3.ZERO)
		placed += _lay(world, Vector3(c.x, CEIL_Y, c.z), Vector3(PI, 0.0, 0.0))
	print("ZFLOOR pieces=", placed, " cells=", cells.size())
	return placed


func _lay(world: Node3D, pos: Vector3, rot: Vector3) -> int:
	var scene: PackedScene = _cache
	if scene == null:
		return 0
	var inst: Node3D = scene.instantiate()
	_seq += 1
	inst.name = "ZF_brick_%03d" % _seq
	world.add_child(inst)
	inst.global_position = pos
	inst.rotation = rot
	return 1
