extends SceneTree
## Headless verification of the between-raid shop economy.
## Run: godot --headless --path . --script tests/test_shop.gd

var fails := 0
var stash_ref: Node = null

func _initialize() -> void:
	if not root.has_node("Stash"):
		var stash := Node.new()
		stash.name = "Stash"
		stash.set_script(load("res://game/scripts/stash.gd"))
		root.add_child(stash)
	stash_ref = root.get_node("Stash")
	_run.call_deferred()

func _check(name: String, ok: bool) -> void:
	print(("PASS " if ok else "FAIL ") + name)
	if not ok:
		fails += 1

func _run() -> void:
	# Fresh economy state
	stash_ref.banked_loot = 0
	stash_ref.upgrades = {"health": 0, "speed": 0, "loot": 0, "medkit": 0}

	_check("base cost health = 300", stash_ref.upgrade_cost("health") == 300)
	_check("cannot buy while broke", not stash_ref.buy_upgrade("health"))
	_check("level stays 0", stash_ref.upgrade_level("health") == 0)

	# Affordable purchase
	stash_ref.banked_loot = 700
	_check("buy health lvl1", stash_ref.buy_upgrade("health"))
	_check("spent 300", stash_ref.banked_loot == 400)
	_check("cost escalates to 600", stash_ref.upgrade_cost("health") == 600)
	_check("cannot afford lvl2", not stash_ref.buy_upgrade("health"))

	# Loot value bonus maths via a second purchase path
	stash_ref.banked_loot += 1000
	_check("buy health lvl2", stash_ref.buy_upgrade("health"))
	_check("escalation consumed 600", stash_ref.banked_loot == 800)

	# Max cap: medkit is a single level
	stash_ref.banked_loot += 1000
	_check("buy medkit", stash_ref.buy_upgrade("medkit"))
	_check("medkit maxed", stash_ref.upgrade_maxed("medkit"))
	_check("cannot rebuy medkit", not stash_ref.buy_upgrade("medkit"))

	# Unknown ids are rejected safely
	_check("unknown id rejected", not stash_ref.buy_upgrade("does_not_exist"))

	print("RESULT: %s (%d fails)" % ["OK" if fails == 0 else "FAILED", fails])
	quit(1 if fails > 0 else 0)
