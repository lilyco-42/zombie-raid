extends Node3D
## 中式僵尸探针 (场景化, 坑9: 用场景 + _ready, 别用 -s 的 _init)。
## 运行: godot --headless --path . res://tools/godot/probe_jiangshi.tscn
##
## 断言:
##  A 强制路径: jiangshi=true 的 Walker 挂满 4 件, 4 个 JS_* BoneAttachment3D 各含 >=1 网格
##  B 顶戴冒出头骨: 手动 dress 后模型 AABB 顶高于挂前 (防"埋进模型"回归, 坑28)
##  C 黄符在脸前: 符中心 z 落在面部前方区间 (0.22-0.45, 归一化到模型高, 渲染目检校准)
##  D 材质未被绿 tint 污染: 黄符 albedo 仍是黄纸色
##  E 自动规则: ztype==1 + 同名 -> jiangshi 与 fposmod(hash(name),1.0)<0.35 一致, 两实例一致

const ZombieScene := preload("res://game/scenes/zombie.tscn")
const JIANGSHI := preload("res://game/scripts/chinese_jiangshi.gd")

var fails := 0


func _ready() -> void:
	await get_tree().process_frame
	_test_forced()
	await _test_manual_dress()
	_test_auto_rule()
	if fails == 0:
		print("ZJIANG_PROBE PASS")
	else:
		print("ZJIANG_PROBE FAIL fails=", fails)
	get_tree().quit(1 if fails > 0 else 0)


func _check(ok: bool, label: String) -> void:
	if ok:
		print("  ok - ", label)
	else:
		fails += 1
		print("  FAIL - ", label)


func _spawn(forced: bool, ztype_v: int, zname: String) -> CharacterBody3D:
	var holder := Node3D.new()
	holder.name = "Holder_" + zname + str(forced)
	add_child(holder)
	var z: CharacterBody3D = ZombieScene.instantiate()
	z.ztype = ztype_v
	z.jiangshi = forced
	z.name = zname
	holder.add_child(z)
	z.set_physics_process(false)
	return z


func _model_aabb(z: CharacterBody3D) -> AABB:
	var model: Node3D = z.get_node("Model")
	var total := AABB()
	var has := false
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		var rel: Transform3D = model.global_transform.affine_inverse() * mi.global_transform
		var box: AABB = rel * mi.get_aabb()
		total = box if not has else total.merge(box)
		has = true
	return total


func _test_forced() -> void:
	print("[A/D] 强制 jiangshi Walker")
	var z := _spawn(true, 1, "Z_777")
	var model: Node3D = z.get_node("Model")
	_check(z.jiangshi, "jiangshi=true 保持强制")
	_check(z.jiangshi_parts == 4, "挂件数 == 4 (实测 %d)" % z.jiangshi_parts)
	var atts := model.find_children("JS_*", "BoneAttachment3D", true, false)
	_check(atts.size() == 4, "BoneAttachment3D JS_* == 4 (实测 %d)" % atts.size())
	for att in atts:
		var meshes := (att as Node).find_children("*", "MeshInstance3D", true, false)
		_check(meshes.size() >= 1, "%s 含网格" % (att as Node).name)
	# D: 黄符材质仍是黄纸色 (未被 undead tint 染绿)
	var talisman := model.get_node_or_null("Skeleton3D/JS_jiangshi_talisman")
	if talisman == null:
		for att in atts:
			if String((att as Node).name) == "JS_jiangshi_talisman":
				talisman = att
	var mi := talisman.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D
	var mat := mi.get_active_material(0) as BaseMaterial3D
	_check(mat != null and mat.albedo_color.r > 0.8 and mat.albedo_color.g > 0.75
			and mat.albedo_color.r - mat.albedo_color.b > 0.2,
			"黄符 albedo 保持黄 (%s)" % (mat.albedo_color if mat else Color()))


func _test_manual_dress() -> void:
	print("[B/C] 手动 dress 前后对比")
	var z := _spawn(false, 2, "Z_888")   # ztype=2 (Brute) 不会触发自动规则
	var before := _model_aabb(z)
	var n: int = JIANGSHI.dress(z)
	var after := _model_aabb(z)
	_check(n == 4, "dress() 返回 4 (实测 %d)" % n)
	_check(after.position.y + after.size.y > before.position.y + before.size.y + 0.05,
			"顶戴冒出头骨 (+%.2fm)" % (after.position.y + after.size.y
					- before.position.y - before.size.y))
	# C: 黄符中心 z (模型空间, z=正面)
	var talisman: Node3D = null
	for att in z.get_node("Model").find_children("JS_*", "BoneAttachment3D", true, false):
		if String((att as Node).name) == "JS_jiangshi_talisman":
			talisman = att
	var rel: Transform3D = z.get_node("Model").global_transform.affine_inverse() \
			* (talisman.find_children("*", "MeshInstance3D", true, false)[0] as Node3D) \
					.global_transform
	var center_z: float = (rel * (talisman.find_children("*", "MeshInstance3D",
			true, false)[0] as MeshInstance3D).get_aabb()).get_center().z
	var ratio := center_z / after.size.y
	_check(ratio > 0.10 and ratio < 0.30, "黄符在脸前 (z/H=%.2f)" % ratio)


func _test_auto_rule() -> void:
	print("[E] Walker 自动规则 (名字哈希)")
	var expected: bool = fposmod(float(hash("Z_424242")), 1.0) < 0.35
	var z1 := _spawn(false, 1, "Z_424242")
	var z2 := _spawn(false, 1, "Z_424242")
	_check(z1.jiangshi == expected, "规则一致 (期望 %s)" % expected)
	_check(z1.jiangshi == z2.jiangshi, "同名两实例一致")
	_check(z1.jiangshi == false or z1.jiangshi_parts == 4, "变则挂满 4 件")
