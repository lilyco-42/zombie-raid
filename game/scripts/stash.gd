extends Node
## Autoload singleton "Stash": state that survives between raids.
## Success extraction banks the loot you carried out; dying loses it.

var banked_loot: int = 0
var lifetime_kills: int = 0
var successful_extractions: int = 0
var quota: int = 500  # Lethal Company style: met quotas double forever

# --- Permanent upgrades bought between raids ---
# Level costs escalate: base_cost * 2^level, capped at MAX_LEVEL each.
const UPGRADE_DEFS := {
	"health": {"name": "MAX HP +25", "base": 300, "max": 6},
	"speed": {"name": "MOVE SPEED +6%", "base": 400, "max": 4},
	"loot": {"name": "LOOT VALUE +12%", "base": 500, "max": 5},
	"medkit": {"name": "START WITH MEDKIT", "base": 350, "max": 1},
}
var upgrades := {"health": 0, "speed": 0, "loot": 0, "medkit": 0}

func upgrade_cost(id: String) -> int:
	var level: int = upgrades.get(id, 0)
	return int(UPGRADE_DEFS[id]["base"]) * int(pow(2.0, level))

func upgrade_maxed(id: String) -> bool:
	return upgrades.get(id, 0) >= int(UPGRADE_DEFS[id]["max"])

func buy_upgrade(id: String) -> bool:
	if not UPGRADE_DEFS.has(id) or upgrade_maxed(id):
		return false
	var cost := upgrade_cost(id)
	if banked_loot < cost:
		return false
	banked_loot -= cost
	upgrades[id] = upgrades.get(id, 0) + 1
	return true

func upgrade_level(id: String) -> int:
	return upgrades.get(id, 0)
