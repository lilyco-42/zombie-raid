extends Node
## Autoload singleton "Stash": state that survives between raids.
## Success extraction banks the loot you carried out; dying loses it.

var banked_loot: int = 0
var lifetime_kills: int = 0
var successful_extractions: int = 0
var quota: int = 500  # Lethal Company style: met quotas double forever
