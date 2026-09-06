extends SceneTree
## Headless verification: facility spitter's acid projectile damages the player.
## Run: godot --headless --path . --script tests/test_spitter.gd

var fails := 0

func _initialize() -> void:
	# --script mode may skip autoloads; provide them manually where needed
	if not root.has_node("Sfx"):
		var sfx := Node.new()
		sfx.name = "Sfx"
		sfx.set_script(load("res://game/scripts/sfx.gd"))
		root.add_child(sfx)
	_run.call_deferred()

func _check(name: String, ok: bool) -> void:
	print(("PASS " if ok else "FAIL ") + name)
	if not ok:
		fails += 1

func _run() -> void:
	var world := Node3D.new()
	root.add_child(world)

	# Floor so gravity keeps both actors grounded
	var floor_body := StaticBody3D.new()
	var fcs := CollisionShape3D.new()
	var fbox := BoxShape3D.new()
	fbox.size = Vector3(40, 1, 40)
	fcs.shape = fbox
	fcs.position.y = -0.5
	floor_body.add_child(fcs)
	world.add_child(floor_body)

	# Dummy player 8m away
	var dummy: CharacterBody3D = load("res://tests/dummy_player.gd").new()
	world.add_child(dummy)
	dummy.global_position = Vector3(0, 0, 8)

	# Spitter at the origin (default Minion model keeps the test light)
	var spitter: CharacterBody3D = load("res://game/scenes/zombie.tscn").instantiate()
	spitter.set_script(load("res://game/scripts/spitter.gd"))
	world.add_child(spitter)
	spitter.global_position = Vector3(0, 0, 0)
	await process_frame
	await process_frame

	_check("spitter script applied", spitter.get_script().resource_path.ends_with("spitter.gd"))

	# Force an attack; the spit launches 0.45s later and flies 8m
	spitter._do_attack(dummy)
	for i in 120:  # up to 2s of physics
		await physics_frame
		if dummy.damage_taken > 0.0:
			break
	_check("acid projectile damaged the player (%.0f)" % dummy.damage_taken, dummy.damage_taken >= 10.0)

	# Frenzy inherits: speeds multiply
	var before: float = spitter.run_speed
	spitter.frenzy()
	_check("spitter frenzy inherits", spitter.run_speed > before * 1.4)

	print("RESULT: %s (%d fails)" % ["OK" if fails == 0 else "FAILED", fails])
	quit(1 if fails > 0 else 0)
