extends Node
## 鼠标锁定守卫 (WASM 关键)。
##
## 浏览器的 pointer lock 一旦丢失 (ESC / 切窗口 / 点到画布外), 不会自己回来,
## 表现就是"鼠标滑到屏幕边缘就转不动了"。这里做两件事:
##   1. 未锁定时盖一层半透明提示 + 文案 (i18n);
##   2. 任意点击/按键重新请求锁定 (浏览器要求用户手势, 点击最稳)。
## 用法: 由 world_raid 在开局后 set_enabled(true), 商店/结算界面 set_enabled(false)。

const I18n := preload("res://game/scripts/i18n.gd")

var enabled := false

var _layer: CanvasLayer
var _panel: PanelContainer
var _label: Label


func _ready() -> void:
	_build_hint()
	set_process(true)
	set_process_input(true)


func _build_hint() -> void:
	_layer = CanvasLayer.new()
	_layer.name = "PointerLockHint"
	_layer.layer = 30
	add_child(_layer)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.add_child(root)
	var dim := ColorRect.new()
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0, 0, 0, 0.45)
	root.add_child(dim)
	_label = Label.new()
	_label.set_anchors_preset(Control.PRESET_CENTER)
	_label.offset_left = -320
	_label.offset_right = 320
	_label.offset_top = -30
	_label.offset_bottom = 30
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_label.add_theme_font_size_override("font_size", 26)
	_label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	_label.add_theme_constant_override("outline_size", 8)
	_label.text = I18n.t("click_to_lock")
	root.add_child(_label)
	_layer.visible = false


func set_enabled(value: bool) -> void:
	enabled = value
	if enabled:
		_capture()
	else:
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)
		_layer.visible = false


func _capture() -> void:
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)


func _process(_delta: float) -> void:
	if not enabled:
		return
	var locked := Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED
	_layer.visible = not locked
	if _label.text != I18n.t("click_to_resume"):
		_label.text = I18n.t("click_to_resume")


func _input(event: InputEvent) -> void:
	if not enabled:
		return
	if Input.get_mouse_mode() == Input.MOUSE_MODE_CAPTURED:
		return
	# 浏览器要求用户手势才能重新锁定: 点击最稳, 按键兜底
	if event is InputEventMouseButton and event.pressed:
		_capture()
		get_viewport().set_input_as_handled()
	elif event is InputEventKey and event.pressed and not event.echo:
		_capture()
