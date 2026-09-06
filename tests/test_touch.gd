extends SceneTree
## Headless verification of the touch control wiring.
## All positions are taken from the live viewport at runtime, so this works
## under any window size (headless reports a 64x64 viewport).
## Run: godot --headless --path . --script tests/test_touch.gd

var fails := 0

func _initialize() -> void:
	var tc: CanvasLayer = load("res://game/scripts/touch_controls.gd").new()
	root.add_child(tc)
	_run.call_deferred(tc)

func _touch(index: int, pos: Vector2, pressed: bool) -> void:
	var t := InputEventScreenTouch.new()
	t.index = index
	t.position = pos
	t.pressed = pressed
	Input.parse_input_event(t)

func _drag(index: int, pos: Vector2) -> void:
	var d := InputEventScreenDrag.new()
	d.index = index
	d.position = pos
	Input.parse_input_event(d)

func _check(name: String, ok: bool) -> void:
	print(("PASS " if ok else "FAIL ") + name)
	if not ok:
		fails += 1

func _run(tc: CanvasLayer) -> void:
	await process_frame
	await process_frame
	var vp: Vector2 = tc._vp()
	print("viewport: ", vp)

	# 1) FIRE button -> Shoot action held (both event and state channels)
	var fire := Vector2(vp.x * 0.880, vp.y * 0.78)
	_touch(1, fire, true)
	await process_frame
	_check("FIRE button holds Shoot", Input.is_action_pressed("Shoot"))
	_touch(1, fire, false)
	await process_frame
	_check("FIRE release drops Shoot", not Input.is_action_pressed("Shoot"))

	# 2) Joystick drag right -> analog strength on "right"
	var base: Control = tc._joystick.get_node("Base")
	var start: Vector2 = base.global_position + base.size * 0.5
	_touch(2, start, true)
	await process_frame
	_drag(2, start + Vector2(vp.x * 0.08, 0))
	await process_frame
	_check("Joystick drives right strength", Input.get_action_strength("right") > 0.2)
	_touch(2, start + Vector2(vp.x * 0.08, 0), false)
	await process_frame

	# 3) Look drag on right half -> synthesized mouse motion reaches _input
	var probe := Node.new()
	probe.set_script(load("res://tests/look_probe.gd"))
	root.add_child(probe)
	await process_frame
	var look_start := Vector2(vp.x * 0.9, vp.y * 0.5)
	_touch(3, look_start, true)
	await process_frame
	_drag(3, look_start + Vector2(vp.x * 0.1, vp.y * 0.02))
	await process_frame
	_check("Look drag synthesizes mouse motion", probe.last_relative.x > vp.x * 0.05)

	# 4) V button -> toggle_view action state
	var vpos := Vector2(vp.x * 0.935, vp.y * 0.40)
	_touch(4, vpos, true)
	await process_frame
	_check("V button holds toggle_view", Input.is_action_pressed("toggle_view"))
	_touch(4, vpos, false)
	await process_frame

	print("RESULT: %s (%d fails)" % ["OK" if fails == 0 else "FAILED", fails])
	quit(1 if fails > 0 else 0)
