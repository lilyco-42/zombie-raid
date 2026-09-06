extends Node
## Test probe: records the last synthesized mouse motion relative.

var last_relative := Vector2.ZERO

func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		last_relative = event.relative
