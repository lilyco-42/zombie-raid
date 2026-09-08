extends CanvasLayer
## 新手引导 —— 开局罩一层, 列出键位 (i18n), 任意键/点击即关闭并把鼠标交回游戏。
## 独立成文件, 不改商店与 HUD。

signal dismissed

const I18n := preload("res://game/scripts/i18n.gd")

const ROWS := [
	["hint_move", "key_wasd"],
	["hint_sprint", "key_shift"],
	["hint_crouch", "key_ctrl"],
	["hint_jump", "key_space"],
	["hint_shoot", "key_lmb"],
	["hint_aim", "key_rmb"],
	["hint_reload", "key_r"],
	["hint_interact", "key_e"],
	["hint_scan", "key_mmb"],
	["hint_flashlight", "key_t"],
	["hint_view", "key_v"],
]


func _ready() -> void:
	layer = 40
	_build()
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)


func _build() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(root)
	var dim := ColorRect.new()
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.02, 0.02, 0.03, 0.72)
	root.add_child(dim)

	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.offset_left = -260
	panel.offset_right = 260
	panel.offset_top = -230
	panel.offset_bottom = 230
	root.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	panel.add_child(vbox)

	var title := Label.new()
	title.text = I18n.t("tutorial_title")
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 28)
	vbox.add_child(title)

	for pair in ROWS:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 16)
		vbox.add_child(row)
		var action := Label.new()
		action.text = I18n.t(pair[0])
		action.custom_minimum_size = Vector2(150, 0)
		action.add_theme_font_size_override("font_size", 18)
		row.add_child(action)
		var key := Label.new()
		key.text = I18n.t(pair[1])
		key.custom_minimum_size = Vector2(150, 0)
		key.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		key.add_theme_font_size_override("font_size", 18)
		key.add_theme_color_override("font_color", Color(0.95, 0.82, 0.42))
		row.add_child(key)

	var hint := Label.new()
	hint.text = I18n.t("dismiss")
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 18)
	hint.modulate.a = 0.85
	vbox.add_child(hint)


func _input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		_close()
	elif event is InputEventMouseButton and event.pressed:
		_close()


func _close() -> void:
	dismissed.emit()
	queue_free()
