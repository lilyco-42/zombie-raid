extends "res://raid/scripts/zombie.gd"
## Facility spitter: a KayKit Mage that lobs acid projectiles from range.
## Melee claw if the player gets close; frenzy inherits from the base zombie.

const SpitProjectile := preload("res://raid/scripts/spit_projectile.gd")

const SPIT_DELAY := 0.45
const SPIT_MAX_RANGE := 18.0
const SPIT_MELEE_RANGE := 2.4

func _do_attack(player: Node3D) -> void:
	if _attack_timer > 0.0:
		return
	_attack_timer = ATTACK_COOLDOWN
	state = State.ATTACK
	velocity.x = 0
	velocity.z = 0
	_face_position(player.global_position)
	if anim and anim.has_animation("Spellcast_Shoot"):
		anim.play("Spellcast_Shoot")
	get_tree().create_timer(SPIT_DELAY).timeout.connect(func():
		if state == State.DEAD:
			return
		var p := _find_player()
		if p == null:
			return
		var dist := global_position.distance_to(p.global_position)
		if dist > SPIT_MAX_RANGE:
			return
		if dist < SPIT_MELEE_RANGE and p.has_method("get_damage"):
			p.get_damage(attack_damage)  # point blank: claw instead
			Sfx.flesh_hit(global_position)
			return
		_launch_spit(p.global_position + Vector3(0, 1.2, 0))
	)

func _launch_spit(target: Vector3) -> void:
	var spit := Area3D.new()
	spit.set_script(SpitProjectile)
	get_parent().add_child(spit)
	spit.launch(global_position + Vector3(0, 1.5, 0), target)
	Sfx.spit(global_position)
