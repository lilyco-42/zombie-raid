extends SceneTree
## Headless verification: PUBG-style TP sync + zombie no-navmesh fallback.

var fails := 0

func _check(name: String, ok: bool) -> void:
	print(("PASS " if ok else "FAIL ") + name)
	if not ok:
		fails += 1

func _initialize() -> void:
	var player: CharacterBody3D = load("res://vendor/Player_Controller/player_character.tscn").instantiate()
	root.add_child(player)
	player.add_to_group("player")
	var avatar: Node3D = load("res://game/scripts/player_avatar.gd").new()
	player.add_child(avatar)
	_run.call_deferred(player, avatar)

func _run(player: CharacterBody3D, avatar: Node3D) -> void:
	await process_frame
	await process_frame

	# --- 1) TP orbit: synthetic mouse motion rotates the ROOT, rig follows ---
	avatar.fp_mode = false
	avatar._apply_mode()
	var yaw_before: float = player.global_rotation.y
	var mm := InputEventMouseMotion.new()
	mm.relative = Vector2(100, 0)
	Input.parse_input_event(mm)
	await process_frame
	await process_frame
	_check("TP: mouse orbits character root", absf(player.global_rotation.y - yaw_before) > 0.05)

	# --- 2) TP->FP sync: view snaps to the ORBIT yaw (root), PUBG-style ---
	var want_facing := Vector3(-sin(player.global_rotation.y), 0.0, -cos(player.global_rotation.y))
	avatar.fp_mode = true
	avatar._apply_mode()
	await process_frame
	var cam: Camera3D = avatar.fp_camera  # the template's real FP camera (MainCamera)
	var fwd := -cam.global_transform.basis.z
	fwd.y = 0
	fwd = fwd.normalized()
	_check("TP->FP sync: camera forward matches body facing", fwd.dot(want_facing) > 0.85)

	# --- 3) Zombie fallback movement without a navmesh (headless never bakes) ---
	var zombie: CharacterBody3D = load("res://game/scenes/zombie.tscn").instantiate()
	root.add_child(zombie)
	# The template player (group "player") sits at the origin; push it away so
	# the zombie chases instead of melee-locking at zero distance
	player.global_position = Vector3(30, 0, 0)
	zombie.global_position = Vector3.ZERO
	await process_frame
	zombie.state = 2  # State.CHASE
	var frames := 0
	while frames < 90:
		await physics_frame
		frames += 1
	var horizontal := Vector3(zombie.global_position.x, 0, zombie.global_position.z).length()
	_check("Zombie fallback: moves toward player without navmesh", horizontal > 1.0)

	print("RESULT: %s (%d fails)" % ["OK" if fails == 0 else "FAILED", fails])
	quit(1 if fails > 0 else 0)
