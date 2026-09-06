extends CharacterBody3D
## Test double: a stand-in player that records incoming damage.

var damage_taken := 0.0

func _ready() -> void:
	add_to_group("player")
	var cs := CollisionShape3D.new()
	var sh := CapsuleShape3D.new()
	sh.radius = 0.4
	sh.height = 1.5
	cs.shape = sh
	cs.position.y = 0.75
	add_child(cs)

func get_damage(amount: float, _direction: Vector3 = Vector3.ZERO, _position: Vector3 = Vector3.ZERO) -> void:
	damage_taken += amount
