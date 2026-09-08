extends RefCounted
## 中式渐进 · 生灵级: 僵尸 (jiangshi) 骨骼挂件挂接器 (Round 49)。
##
## 不做人形模型、不做绑定、不做动画 —— 用 BoneAttachment3D 把四件中式配件挂到
## KayKit 骷髅的 head/chest/hips 骨上, 让既有骷髅变成"清朝僵尸":
##   jiangshi_hat       清式顶戴 (黑缎帽 + 金座 + 红顶珠)   -> head
##   jiangshi_talisman  额前黄符 (黄纸 + 朱砂符纹)          -> head
##   jiangshi_buzi      胸背方补 (靛蓝补子 + 金边 + 金兽纹) -> chest
##   jiangshi_coins     腰间铜钱串 (4 枚铜钱 + 串绳)        -> hips
##
## !! 偏移数值来自蒙皮网格实测 (坑28, tools/blender/build_chinese_jiangshi.py 头注释):
## KayKit 骨骼 rest 位置远小于蒙皮网格 (头骨蒙皮后 0.87m 高), 按骨骼点位目测的偏移
## 会把挂件整体埋进模型。数值在 Blender 端用蒙皮包围盒校过 + 渲染目检三视图通过。
##
## 坐标约定: 骨架空间 y=上, z=正面 (KayKit 模型面朝 +Z, 与 zombie.gd _face_dir 一致)。

const ZH := "res://assets/static/vendor/chinese/"

# [glb 名, 骨名, 沿骨架上方向偏移, 沿正面方向偏移] — 与 build/render 脚本 SPECS 一致
const SPECS: Array = [
	["jiangshi_hat", "head", 0.810, 0.0],
	["jiangshi_talisman", "head", 0.600, 0.400],
	["jiangshi_buzi", "chest", 0.030, 0.371],
	["jiangshi_coins", "hips", 0.194, 0.240],
]

## 僵尸皮肤青灰 (盖掉 Walker 的荧光绿 tint, 只动基础骷髅, 不碰挂件材质)
const CORPSE_TINT := Color(0.58, 0.68, 0.64)


static func dress(zombie: Node3D) -> int:
	## 给一只僵尸挂全套配件, 返回成功挂上的件数。
	var model := zombie.get_node_or_null("Model") as Node3D
	if model == null:
		return 0
	var skel := _find_skeleton(model)
	if skel == null:
		return 0
	_retint_base(model, skel)
	var n := 0
	for spec in SPECS:
		if _attach_one(skel, spec[0], spec[1], spec[2], spec[3]):
			n += 1
	return n


static func _attach_one(skel: Skeleton3D, glb: String, bone: String,
		up_off: float, fwd_off: float) -> bool:
	var idx := skel.find_bone(bone)
	if idx < 0:
		push_warning("JIANGSHI bone not found: " + bone)
		return false
	var scene: PackedScene = load(ZH + glb + ".glb")
	if scene == null:
		push_warning("JIANGSHI glb not found: " + glb)
		return false
	var att := BoneAttachment3D.new()
	att.name = "JS_" + glb
	att.bone_name = bone
	skel.add_child(att)
	var inst: Node3D = scene.instantiate()
	att.add_child(inst)
	# 挂件期望位姿 (骨架空间): 骨点 + up/fwd 偏移, 朝向与骨架对齐 (GLB 已按
	# y-up/正面+Z 导出)。挂件局部 = 骨骼位姿逆 * 期望位姿, 之后随骨骼动画走。
	var pose := skel.get_bone_global_pose(idx)
	var want := Transform3D(Basis.IDENTITY,
			pose.origin + Vector3(0.0, up_off, fwd_off))
	inst.transform = pose.affine_inverse() * want
	return true


static func _find_skeleton(model: Node3D) -> Skeleton3D:
	var found: Skeleton3D = null
	for node in model.find_children("*", "Skeleton3D", true, false):
		found = node
		break
	return found


static func _retint_base(model: Node3D, skel: Skeleton3D) -> void:
	## 只把基础骷髅的 override 材质改成青灰; 挂件 (JS_* 子树) 保持原色。
	for mi in model.find_children("*", "MeshInstance3D", true, false):
		if _under_jiangshi(mi as Node, skel):
			continue
		for i in mi.get_surface_override_material_count():
			var m: Material = mi.get_surface_override_material(i)
			if m is BaseMaterial3D:
				m.albedo_color = CORPSE_TINT


static func _under_jiangshi(node: Node, skel: Skeleton3D) -> bool:
	var cur := node
	while cur != null and cur != skel:
		if String(cur.name).begins_with("JS_"):
			return true
		cur = cur.get_parent()
	return false
