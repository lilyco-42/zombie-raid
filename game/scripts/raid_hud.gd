extends CanvasLayer
## Raid HUD, built entirely in code: health bar, loot counters,
## center messages, extraction progress bar and a red damage flash.

const I18n := preload("res://game/scripts/i18n.gd")

var _health_bar: ProgressBar
var _health_label: Label
var _loot_label: Label
var _msg_label: Label
var _extract_box: VBoxContainer
var _extract_bar: ProgressBar
var _flash: ColorRect
var _msg_tween: Tween
var _clock_label: Label
var _ammo_label: Label
var _keys_label: Label

func _ready() -> void:
	layer = 10
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	# Damage flash overlay
	_flash = ColorRect.new()
	_flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	_flash.color = Color(0.8, 0.0, 0.0, 0.0)
	_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_flash)

	# Top-center countdown clock
	_clock_label = _make_label(26)
	_clock_label.anchor_left = 0.5
	_clock_label.anchor_right = 0.5
	_clock_label.offset_left = -300
	_clock_label.offset_right = 300
	_clock_label.offset_top = 8
	_clock_label.offset_bottom = 46
	_clock_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root.add_child(_clock_label)

	# Top-left status block
	var top := VBoxContainer.new()
	top.position = Vector2(16, 12)
	top.add_theme_constant_override("separation", 4)
	root.add_child(top)
	_loot_label = _make_label(20)
	top.add_child(_loot_label)

	# Bottom-left health
	var bottom := VBoxContainer.new()
	bottom.anchor_left = 0.0
	bottom.anchor_right = 0.0
	bottom.anchor_top = 1.0
	bottom.anchor_bottom = 1.0
	bottom.offset_left = 16
	bottom.offset_top = -74
	bottom.offset_right = 500
	bottom.offset_bottom = -10
	bottom.add_theme_constant_override("separation", 4)
	root.add_child(bottom)
	_health_label = _make_label(16)
	bottom.add_child(_health_label)
	_health_bar = ProgressBar.new()
	_health_bar.custom_minimum_size = Vector2(280, 22)
	_health_bar.min_value = 0
	_health_bar.max_value = 100
	_health_bar.value = 100
	_health_bar.show_percentage = false
	var bar_style := StyleBoxFlat.new()
	bar_style.bg_color = Color(0.7, 0.1, 0.1)
	bar_style.corner_radius_top_left = 4
	bar_style.corner_radius_top_right = 4
	bar_style.corner_radius_bottom_left = 4
	bar_style.corner_radius_bottom_right = 4
	var bg_style := StyleBoxFlat.new()
	bg_style.bg_color = Color(0.1, 0.1, 0.12, 0.8)
	bg_style.corner_radius_top_left = 4
	bg_style.corner_radius_top_right = 4
	bg_style.corner_radius_bottom_left = 4
	bg_style.corner_radius_bottom_right = 4
	_health_bar.add_theme_stylebox_override("fill", bar_style)
	_health_bar.add_theme_stylebox_override("background", bg_style)
	bottom.add_child(_health_bar)

	# Center message
	_msg_label = _make_label(30)
	_msg_label.anchor_left = 0.5
	_msg_label.anchor_right = 0.5
	_msg_label.offset_left = -500
	_msg_label.offset_right = 500
	_msg_label.offset_top = 110
	_msg_label.offset_bottom = 170
	_msg_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_msg_label.modulate.a = 0.0
	root.add_child(_msg_label)

	# Extraction progress (center-bottom)
	_extract_box = VBoxContainer.new()
	_extract_box.anchor_left = 0.5
	_extract_box.anchor_right = 0.5
	_extract_box.anchor_top = 1.0
	_extract_box.anchor_bottom = 1.0
	_extract_box.offset_left = -130
	_extract_box.offset_right = 130
	_extract_box.offset_top = -160
	_extract_box.offset_bottom = -90
	_extract_box.visible = false
	root.add_child(_extract_box)
	var extract_label := _make_label(20)
	extract_label.text = I18n.t("extracting")
	extract_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_extract_box.add_child(extract_label)
	_extract_bar = ProgressBar.new()
	_extract_bar.custom_minimum_size = Vector2(240, 18)
	_extract_bar.max_value = 1.0
	_extract_bar.show_percentage = false
	var green := StyleBoxFlat.new()
	green.bg_color = Color(0.1, 0.8, 0.3)
	_extract_bar.add_theme_stylebox_override("fill", green)
	_extract_bar.add_theme_stylebox_override("background", bg_style.duplicate())
	_extract_box.add_child(_extract_bar)

	# Bottom-right: 弹药
	_ammo_label = _make_label(26)
	_ammo_label.anchor_left = 1.0
	_ammo_label.anchor_right = 1.0
	_ammo_label.anchor_top = 1.0
	_ammo_label.anchor_bottom = 1.0
	_ammo_label.offset_left = -420
	_ammo_label.offset_right = -20
	_ammo_label.offset_top = -78
	_ammo_label.offset_bottom = -44
	_ammo_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_ammo_label.text = "%s  -- / --" % I18n.t("ammo")
	root.add_child(_ammo_label)

	# Bottom-right: 键位速查 (常驻)
	_keys_label = _make_label(14)
	_keys_label.anchor_left = 1.0
	_keys_label.anchor_right = 1.0
	_keys_label.anchor_top = 1.0
	_keys_label.anchor_bottom = 1.0
	_keys_label.offset_left = -620
	_keys_label.offset_right = -20
	_keys_label.offset_top = -40
	_keys_label.offset_bottom = -8
	_keys_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_keys_label.modulate.a = 0.72
	_keys_label.text = _key_hints()
	root.add_child(_keys_label)

func _key_hints() -> String:
	var pairs := [
		[I18n.t("key_wasd"), I18n.t("hint_move")],
		[I18n.t("key_shift"), I18n.t("hint_sprint")],
		[I18n.t("key_ctrl"), I18n.t("hint_crouch")],
		[I18n.t("key_space"), I18n.t("hint_jump")],
		[I18n.t("key_lmb"), I18n.t("hint_shoot")],
		[I18n.t("key_rmb"), I18n.t("hint_aim")],
		[I18n.t("key_r"), I18n.t("hint_reload")],
		[I18n.t("key_e"), I18n.t("hint_interact")],
		[I18n.t("key_mmb"), I18n.t("hint_scan")],
		[I18n.t("key_t"), I18n.t("hint_flashlight")],
		[I18n.t("key_v"), I18n.t("hint_view")],
	]
	var out := PackedStringArray()
	for pair in pairs:
		out.append("%s %s" % [pair[0], pair[1]])
	return "  |  ".join(out)

func _make_label(size: int) -> Label:
	var l := Label.new()
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	l.add_theme_constant_override("outline_size", 6)
	return l

func set_health(current: float, maximum: float) -> void:
	if maximum <= 0.0:
		return
	_health_bar.max_value = maximum
	_health_bar.value = current
	_health_label.text = "%s  %d / %d" % [I18n.t("hp"), int(current), int(maximum)]

func set_clock(text: String, urgent: bool) -> void:
	_clock_label.text = text
	_clock_label.add_theme_color_override("font_color",
		Color(1.0, 0.25, 0.2) if urgent else Color(1, 1, 1))

func set_status(run_loot: int, banked: int, kills: int, quota: int = -1) -> void:
	if quota >= 0:
		_loot_label.text = "%s $%d  |  %s $%d / %s $%d  |  %s %d" % [
			I18n.t("loot"), run_loot, I18n.t("stash"), banked,
			I18n.t("quota"), quota, I18n.t("kills"), kills]
	else:
		_loot_label.text = "%s $%d   |   %s $%d   |   %s %d" % [
			I18n.t("loot"), run_loot, I18n.t("stash"), banked, I18n.t("kills"), kills]

func set_ammo(current: int, reserve: int) -> void:
	_ammo_label.text = "%s  %d / %d" % [I18n.t("ammo"), current, reserve]

func show_message(text: String, duration := 2.5) -> void:
	_msg_label.text = text
	if _msg_tween and _msg_tween.is_valid():
		_msg_tween.kill()
	_msg_label.modulate.a = 1.0
	_msg_tween = create_tween()
	_msg_tween.tween_interval(duration)
	_msg_tween.tween_property(_msg_label, "modulate:a", 0.0, 0.6)

func set_extraction(active: bool, frac: float) -> void:
	_extract_box.visible = active
	if active:
		_extract_bar.value = frac

func damage_flash() -> void:
	_flash.color.a = 0.35
	var t := create_tween()
	t.tween_property(_flash, "color:a", 0.0, 0.4)
