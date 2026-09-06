extends CanvasLayer
## Mobile touch controls: virtual joystick (borrowed from MarcoFazioRandom's
## MIT Virtual-Joystick-Godot, vendored as virtual_joystick.gd) on the left
## half, look-by-drag on the right half, and an action button cluster.
##
## Wiring tricks (all standard Godot):
## - Joystick drives Input.action_press("left/right/up/down", strength) which
##   feeds the player's Input.get_vector() with analog strength.
## - Look drag synthesizes InputEventMouseMotion, feeding the unmodified
##   mouse-look path of the FPS template.
## - Buttons synthesize InputEventAction (Shoot/Reload/crouch/ui_accept/
##   toggle_view/flashlight), which reach _input/_unhandled_input handlers.
## - Pushing the joystick to the edge auto-holds sprint.

const VirtualJoystickScript := preload("res://raid/scripts/virtual_joystick.gd")

## Multiplier from finger pixels to synthesized mouse-motion pixels.
@export var look_scale := 1.4

var _joystick: Control
var _draw_layer: Control
var _look_index := -1
var _look_last := Vector2.ZERO
var _finger_button := {}   # touch index -> action name
var _pressed_buttons := {}  # action name -> true

# Button layout as viewport fractions (landscape-first)
var _buttons := [
	{"action": "Shoot", "label": "FIRE", "fx": 0.880, "fy": 0.78, "r": 0.086},
	{"action": "ui_accept", "label": "JUMP", "fx": 0.760, "fy": 0.86, "r": 0.061},
	{"action": "Reload", "label": "R", "fx": 0.925, "fy": 0.58, "r": 0.056},
	{"action": "crouch", "label": "C", "fx": 0.785, "fy": 0.63, "r": 0.056},
	{"action": "toggle_view", "label": "V", "fx": 0.935, "fy": 0.40, "r": 0.047},
	{"action": "flashlight", "label": "T", "fx": 0.800, "fy": 0.44, "r": 0.047},
	{"action": "scan", "label": "SCAN", "fx": 0.670, "fy": 0.56, "r": 0.045},
]

func _ready() -> void:
	layer = 20
	_build_joystick()
	_draw_layer = Control.new()
	_draw_layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	_draw_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_draw_layer.draw.connect(_on_draw)
	add_child(_draw_layer)

func _build_joystick() -> void:
	_joystick = Control.new()
	_joystick.set_script(VirtualJoystickScript)
	_joystick.joystick_mode = 1  # DYNAMIC: stick spawns where the thumb lands
	var u: float = _vp().y / 720.0  # UI scale unit (design height 720)
	_joystick.deadzone_size = 14.0 * u
	_joystick.clampzone_size = 85.0 * u
	_joystick.pressed_color = Color(0.4, 0.7, 1.0)
	_joystick.action_left = "left"
	_joystick.action_right = "right"
	_joystick.action_up = "up"
	_joystick.action_down = "down"
	# The joystick claims the LEFT half of the screen (DYNAMIC mode spawns
	# the stick wherever the thumb lands inside this rect)
	_joystick.position = Vector2.ZERO
	_joystick.size = Vector2(_vp().x * 0.45, _vp().y)

	var base := Panel.new()
	base.name = "Base"
	var vw := _vp().x
	var vh := _vp().y
	var u2: float = vh / 720.0
	base.size = Vector2(170, 170) * u2
	base.position = Vector2(60 * u2, vh - 230 * u2)
	base.pivot_offset = base.size * 0.5
	base.add_theme_stylebox_override("panel", _circle_style(Color(1, 1, 1, 0.14), 85 * u2))
	var tip := Panel.new()
	tip.name = "Tip"
	tip.size = Vector2(76, 76) * u2
	tip.position = base.size * 0.5 - tip.size * 0.5
	tip.pivot_offset = tip.size * 0.5
	tip.add_theme_stylebox_override("panel", _circle_style(Color(1, 1, 1, 0.35), 38 * u2))
	base.add_child(tip)
	_joystick.add_child(base)
	add_child(_joystick)

func _circle_style(color: Color, radius: float) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	for corner in ["corner_radius_top_left", "corner_radius_top_right", "corner_radius_bottom_left", "corner_radius_bottom_right"]:
		sb.set(corner, radius)
	return sb

func _vp() -> Vector2:
	if is_inside_tree() and get_viewport():
		return get_viewport().get_visible_rect().size
	return Vector2(1280, 720)

# --- Input routing: buttons first, then look-by-drag on the right half ---
func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed:
			var action := _button_at(event.position)
			if action != "":
				_finger_button[event.index] = action
				_pressed_buttons[action] = true
				_send_action(action, true)
				_draw_layer.queue_redraw()
				get_viewport().set_input_as_handled()
				return
			if event.position.x > _vp().x * 0.45:
				_look_index = event.index
				_look_last = event.position
				get_viewport().set_input_as_handled()
		else:
			if _finger_button.has(event.index):
				var action: StringName = _finger_button[event.index]
				_finger_button.erase(event.index)
				_pressed_buttons[action] = false
				_send_action(action, false)
				_draw_layer.queue_redraw()
				get_viewport().set_input_as_handled()
			elif event.index == _look_index:
				_look_index = -1
	elif event is InputEventScreenDrag and event.index == _look_index:
		var delta: Vector2 = event.position - _look_last
		_look_last = event.position
		var mm := InputEventMouseMotion.new()
		mm.relative = delta * look_scale
		Input.parse_input_event(mm)
		get_viewport().set_input_as_handled()

func _button_at(point: Vector2) -> StringName:
	var size := _vp()
	for b in _buttons:
		var center := Vector2(size.x * b["fx"], size.y * b["fy"])
		if point.distance_to(center) <= float(b["r"]) + _vp().y * 0.025:
			return b["action"]
	return ""

func _send_action(action: StringName, pressed: bool) -> void:
	# Event channel: reaches _input/_unhandled_input handlers (template code).
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = pressed
	Input.parse_input_event(ev)
	# State channel: Input.is_action_pressed() checks (auto-fire, jump buffering).
	if pressed:
		Input.action_press(action)
	else:
		Input.action_release(action)

func _process(_delta: float) -> void:
	# Joystick pushed to the edge = hold sprint
	if _joystick and _joystick.get("output") != null:
		var out: Vector2 = _joystick.get("output")
		if out.length() > 0.9:
			Input.action_press("sprint")
		elif Input.is_action_pressed("sprint"):
			Input.action_release("sprint")

# --- Drawing ---
func _on_draw() -> void:
	var size := _vp()
	var font := ThemeDB.fallback_font
	for b in _buttons:
		var center := Vector2(size.x * b["fx"], size.y * b["fy"])
		var r := float(b["r"]) * size.y
		var action: StringName = b["action"]
		var fill := Color(1.0, 1.0, 0.45, 0.38) if _pressed_buttons.get(action, false) else Color(1, 1, 1, 0.18)
		_draw_layer.draw_circle(center, r, fill)
		_draw_layer.draw_arc(center, r, 0.0, TAU, 48, Color(1, 1, 1, 0.55), 2.0, true)
		_draw_layer.draw_string(font, center + Vector2(-r, 7.0), b["label"],
			HORIZONTAL_ALIGNMENT_CENTER, r * 2.0, 17)
