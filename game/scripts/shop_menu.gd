extends CanvasLayer
## Between-raid shop: pause overlay shown when a raid scene loads. Spend the
## banked stash on permanent upgrades, then DEPLOY to start the run.

signal deployed

const ORDER := ["health", "speed", "loot", "medkit"]

var _root: Control
var _stash_label: Label
var _rows := {}          # id -> {label: Label, button: Button}
var _quota_label: Label

func _ready() -> void:
	layer = 30
	process_mode = Node.PROCESS_MODE_ALWAYS
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(_root)

	var dim := ColorRect.new()
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.color = Color(0.02, 0.03, 0.05, 0.88)
	_root.add_child(dim)

	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.anchor_left = 0.5
	panel.anchor_right = 0.5
	panel.anchor_top = 0.5
	panel.anchor_bottom = 0.5
	panel.offset_left = -260
	panel.offset_right = 260
	panel.offset_top = -230
	panel.offset_bottom = 230
	_root.add_child(panel)
	var pad := MarginContainer.new()
	pad.add_theme_constant_override("margin_left", 24)
	pad.add_theme_constant_override("margin_right", 24)
	pad.add_theme_constant_override("margin_top", 18)
	pad.add_theme_constant_override("margin_bottom", 18)
	panel.add_child(pad)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	pad.add_child(box)

	var title := Label.new()
	title.text = "BLACK MARKET"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 30)
	box.add_child(title)

	_stash_label = Label.new()
	_stash_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_stash_label.add_theme_font_size_override("font_size", 20)
	box.add_child(_stash_label)

	_quota_label = Label.new()
	_quota_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_quota_label.add_theme_font_size_override("font_size", 14)
	_quota_label.modulate = Color(0.7, 0.75, 0.8)
	box.add_child(_quota_label)

	var sep := HSeparator.new()
	box.add_child(sep)

	for id in ORDER:
		box.add_child(_make_row(id))

	var deploy := Button.new()
	deploy.text = "DEPLOY"
	deploy.custom_minimum_size = Vector2(0, 52)
	deploy.add_theme_font_size_override("font_size", 24)
	deploy.pressed.connect(_on_deploy)
	box.add_child(deploy)

	_refresh()
	visible = false

func open() -> void:
	_refresh()
	visible = true
	get_tree().paused = true
	Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

func _on_deploy() -> void:
	visible = false
	get_tree().paused = false
	Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	Sfx.extract_success()
	deployed.emit()

func _make_row(id: String) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	var info: Label = Label.new()
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(info)
	var btn := Button.new()
	btn.custom_minimum_size = Vector2(150, 40)
	btn.pressed.connect(func():
		if Stash.buy_upgrade(id):
			Sfx.loot_pickup(Vector3.ZERO)
			_refresh()
	)
	row.add_child(btn)
	_rows[id] = {"label": info, "button": btn}
	return row

func _refresh() -> void:
	_stash_label.text = "STASH  $%d" % Stash.banked_loot
	_quota_label.text = "next quota  $%d   |   extractions %d   |   kills %d" % [
		Stash.quota, Stash.successful_extractions, Stash.lifetime_kills]
	for id in ORDER:
		var level: int = Stash.upgrade_level(id)
		var maxed: bool = Stash.upgrade_maxed(id)
		var def: Dictionary = Stash.UPGRADE_DEFS[id]
		_rows[id]["label"].text = "%s   [%d/%d]" % [def["name"], level, def["max"]]
		var btn: Button = _rows[id]["button"]
		if maxed:
			btn.text = "MAXED"
			btn.disabled = true
		else:
			var cost: int = Stash.upgrade_cost(id)
			btn.text = "$%d" % cost
			btn.disabled = Stash.banked_loot < cost
