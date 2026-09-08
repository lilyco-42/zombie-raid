extends SceneTree
## LCG64 cross-check against the Rust protocol crate (server/protocol).
## Same seed must produce the same 31-bit outputs on both sides:
## GDScript int64 wrap arithmetic == Rust wrapping u64 ops.
## Reference vectors computed independently (python wrap64).
## Run: godot --headless --path . --script tests/test_lcg.gd

var fails := 0

const SEED := 42
const WANT := [
	1220265334, 484179026, 886563538, 1353769503,
	1460606294, 56326156, 46730969, 327394710,
]

func _initialize() -> void:
	var state: int = SEED
	for w in WANT:
		# mul+add only: wraps mod 2^64 exactly like Rust wrapping_mul/add.
		state = state * 6364136223846793005 + 1442695040888963407
		# shift+mask: arithmetic shift on negatives sign-fills the top bits,
		# which the 31-bit mask discards — identical to Rust's logical shift.
		var got: int = (state >> 33) & 0x7FFFFFFF
		_check("lcg out %d == %d" % [got, w], got == w)
	print("lcg duel done: %s" % ("ALL PASS" if fails == 0 else "%d FAIL" % fails))
	quit(1 if fails > 0 else 0)

func _check(name: String, ok: bool) -> void:
	print(("PASS " if ok else "FAIL ") + name)
	if not ok:
		fails += 1
