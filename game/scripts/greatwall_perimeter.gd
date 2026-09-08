extends Node
## 中式渐变第一层 —— 城市外围的长城 rampart。
##
## 只新增不删改: 独立于 city_builder, 由 world_raid 在导航烘焙前调用,
## 落位在 MAP_HALF 内侧 (半径 30.5), 不碰出生点(最远 ~28.3)/建筑/撤离点。
##
## 形制: 8m 一段砖石墙 (细节墙段/残破段/登城券门段), 四角与两侧骑墙敌楼/烽火台,
## 马道上加障墙; 登城踏道一律朝城内, 玩家可从城里上马道。
## 朝向: Blender 垛口在 +Y → glTF/Godot 为 -Z, 故北墙 yaw=0 / 西墙 +90° /
##       东墙 -90° / 南墙 180°, 垛口一律朝城外。

const ZH := "res://assets/static/vendor/chinese/"

const RADIUS := 30.5          ## 墙段中心线 (城内建筑最远 ~28)
const TOWER_RADIUS := 29.0    ## 敌楼/烽火台进深更大, 往内收避免撞边界墙
const DECK_Y := 5.58          ## 马道面高度 (Blender z -> Godot y)

const SLOTS: Array = [-28.0, -20.0, -12.0, -4.0, 4.0, 12.0, 20.0, 28.0]

const MODEL := {
	"sec": "greatwall_section2",
	"ramp": "greatwall_ramp",
	"ruin": "greatwall_ruin",
	"tower": "greatwall_hollow_tower",
	"beacon": "beacon_tower",
}

var _cache := {}
var _seq := 0


func build(world: Node3D) -> void:
	# 每边 8 个 8m 槽位; 敌楼/烽火台占角或腰, 登城段朝城内
	_side(world, "north", 0.0, ["tower", "sec", "ramp", "sec", "sec", "sec", "ruin", "sec"])
	_side(world, "south", PI, ["sec", "sec", "sec", "ramp", "sec", "sec", "ruin", "tower"])
	_side(world, "east", -PI / 2.0, ["sec", "sec", "ramp", "sec", "sec", "beacon", "sec", "sec"])
	_side(world, "west", PI / 2.0, ["sec", "ruin", "sec", "sec", "ramp", "sec", "sec", "sec"])


func _side(world: Node3D, tag: String, yaw: float, kinds: Array) -> void:
	for i in kinds.size():
		var kind: String = kinds[i]
		var along: float = SLOTS[i]
		var pos := _slot_position(tag, along)
		if kind == "tower" or kind == "beacon":
			pos += _inward(tag) * (RADIUS - TOWER_RADIUS)
		_place(world, String(MODEL[kind]), pos, yaw)
		# 障墙: 马道上的横向护墙 (坡道段护兵), 每三段一个
		if kind == "sec" and i % 3 == 1:
			_place(world, "gw_barrier_wall", pos + Vector3(0.0, DECK_Y, 0.0), yaw)


func _slot_position(tag: String, along: float) -> Vector3:
	match tag:
		"north":
			return Vector3(along, 0.0, -RADIUS)
		"south":
			return Vector3(along, 0.0, RADIUS)
		"east":
			return Vector3(RADIUS, 0.0, along)
		_:
			return Vector3(-RADIUS, 0.0, along)


func _inward(tag: String) -> Vector3:
	match tag:
		"north":
			return Vector3(0.0, 0.0, 1.0)
		"south":
			return Vector3(0.0, 0.0, -1.0)
		"east":
			return Vector3(-1.0, 0.0, 0.0)
		_:
			return Vector3(1.0, 0.0, 0.0)


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
	inst.name = "GW_%s_%02d" % [name, _seq]
	world.add_child(inst)
	inst.global_position = pos
	inst.rotation.y = yaw
	for mi in inst.find_children("*", "MeshInstance3D", true, false):
		mi.create_trimesh_collision()
	return inst
