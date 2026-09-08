extends Area3D
## 弹药补给箱 —— 走上去自动拾取, 直接补当前武器的备弹 (reserve_ammo)。
## 与 loot_box 同一套路: Area3D + player 层碰撞 + 旋转浮动。
## 弹药写回模板的 WeaponSlot, 并触发 Weapons_Manager.update_ammo 让 HUD 刷新。

signal collected(amount: int, box: Area3D)

const BODY_COLOR := Color(0.42, 0.46, 0.22)
const TRIM_COLOR := Color(0.78, 0.66, 0.24)

@export var ammo_amount: int = 30

var _mesh: MeshInstance3D
var _t := randf() * TAU


func _ready() -> void:
	add_to_group("ammo_pickup")
	collision_layer = 0
	collision_mask = 2  # player layer (与 loot_box 一致)
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = Vector3(1.1, 0.9, 1.1)
	cs.shape = sh
	cs.position.y = 0.45
	add_child(cs)
	_build_mesh()
	body_entered.connect(_on_body_entered)


func _build_mesh() -> void:
	# 弹箱: 主体 + 一圈亮色箍带, 一眼能认出是补给
	_mesh = MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(1.0, 0.8, 1.0)
	_mesh.mesh = box
	var mat := StandardMaterial3D.new()
	mat.albedo_color = BODY_COLOR
	mat.roughness = 0.75
	_mesh.material_override = mat
	_mesh.position.y = 0.45
	add_child(_mesh)

	var trim := MeshInstance3D.new()
	var tbox := BoxMesh.new()
	tbox.size = Vector3(1.04, 0.16, 1.04)
	trim.mesh = tbox
	var tmat := StandardMaterial3D.new()
	tmat.albedo_color = TRIM_COLOR
	tmat.roughness = 0.55
	trim.material_override = tmat
	trim.position.y = 0.45
	_mesh.add_child(trim)


func _process(delta: float) -> void:
	_t += delta
	if _mesh:
		_mesh.rotation.y += delta * 1.1
		_mesh.position.y = 0.45 + absf(sin(_t * 2.0)) * 0.10


func _on_body_entered(body: Node3D) -> void:
	if not body.is_in_group("player"):
		return
	var given := _give_ammo(body, ammo_amount)
	if given <= 0:
		return
	collected.emit(given, self)
	queue_free()


func _give_ammo(player: Node3D, amount: int) -> int:
	var wm := player.find_child("Weapons_Manager", true, false)
	if wm == null:
		return 0
	var slot: Resource = wm.get("current_weapon_slot")
	if slot == null:
		return 0
	slot.set("reserve_ammo", int(slot.get("reserve_ammo")) + amount)
	var current := int(slot.get("current_ammo"))
	var reserve := int(slot.get("reserve_ammo"))
	# 模板的信号 -> HUD; 外部 emit 只为刷新显示
	wm.update_ammo.emit([current, reserve])
	return amount
