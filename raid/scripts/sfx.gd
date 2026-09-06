extends Node
## Global sound helper (autoload "Sfx").
## Sources: Kenney Sci-Fi + Interface Sounds (CC0) and generated zombie vocals.
## play_at/play_ui are fire-and-forget one-shots; make_loop hands a looping
## player to the caller, who owns its lifetime.

const DIR := "res://assets/sfx/"
const SHOTS := [
	DIR + "kenney/laserLarge_000.ogg",
	DIR + "kenney/laserLarge_001.ogg",
	DIR + "kenney/laserLarge_002.ogg",
	DIR + "kenney/laserSmall_000.ogg",
	DIR + "kenney/laserSmall_001.ogg",
	DIR + "kenney/laserSmall_002.ogg",
]
const GROWLS := [
	DIR + "gen/zombie_growl_0.wav",
	DIR + "gen/zombie_growl_1.wav",
	DIR + "gen/zombie_growl_2.wav",
]

var _cache := {}

func _stream(path: String) -> AudioStream:
	if not _cache.has(path):
		if ResourceLoader.exists(path):
			_cache[path] = load(path)
		else:
			push_warning("SFX missing: " + path)
			_cache[path] = null
	return _cache[path]

func play_at(path: String, pos: Vector3, volume_db := 0.0, pitch_jitter := 0.0) -> void:
	var s := _stream(path)
	if s == null or get_tree().current_scene == null:
		return
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.volume_db = volume_db
	p.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	p.unit_size = 8.0
	get_tree().current_scene.add_child(p)
	p.global_position = pos
	p.finished.connect(p.queue_free)
	p.play()

func play_ui(path: String, volume_db := 0.0) -> void:
	var s := _stream(path)
	if s == null:
		return
	var p := AudioStreamPlayer.new()
	p.stream = s
	p.volume_db = volume_db
	add_child(p)
	p.finished.connect(p.queue_free)
	p.play()

func _looped(path: String) -> AudioStream:
	var s := _stream(path)
	if s == null:
		return null
	var inst: AudioStream = s.duplicate()
	if inst is AudioStreamOggVorbis:
		inst.loop = true
	else:
		return null  # only ogg looping supported here
	return inst

func make_loop_3d(path: String, volume_db := 0.0) -> AudioStreamPlayer3D:
	var s := _looped(path)
	if s == null:
		return null
	var p := AudioStreamPlayer3D.new()
	p.stream = s
	p.volume_db = volume_db
	p.unit_size = 10.0
	return p

func make_loop_ui(path: String, volume_db := 0.0) -> AudioStreamPlayer:
	var s := _looped(path)
	if s == null:
		return null
	var p := AudioStreamPlayer.new()
	p.stream = s
	p.volume_db = volume_db
	return p

# --- Semantic shortcuts ---
func shot(pos: Vector3) -> void:
	play_at(SHOTS.pick_random(), pos, -4.0, 0.12)

func growl(pos: Vector3) -> void:
	play_at(GROWLS.pick_random(), pos, -2.0, 0.1)

func screech(pos: Vector3) -> void:
	play_at(DIR + "gen/zombie_screech.wav", pos, -2.0, 0.08)

func zombie_death(pos: Vector3) -> void:
	play_at(DIR + "gen/zombie_death.wav", pos, -2.0, 0.06)

func flesh_hit(pos: Vector3) -> void:
	play_at([DIR + "kenney/slime_000.ogg", DIR + "kenney/slime_001.ogg"].pick_random(), pos, -6.0, 0.2)

func loot_pickup(pos: Vector3) -> void:
	play_at(DIR + "kenney/confirmation_002.ogg", pos, -4.0, 0.05)

func medkit_pickup(pos: Vector3) -> void:
	play_at(DIR + "kenney/maximize_003.ogg", pos, -4.0, 0.05)

func player_hurt() -> void:
	play_ui(DIR + "kenney/error_004.ogg", -10.0)

func extract_success() -> void:
	play_ui(DIR + "kenney/confirmation_001.ogg", -2.0)

func raid_failed() -> void:
	play_ui(DIR + "kenney/lowFrequency_explosion_001.ogg", -4.0)

func reload_click(pos: Vector3) -> void:
	play_at(DIR + "kenney/switch_002.ogg", pos, -6.0, 0.1)

func portal_use() -> void:
	play_at(DIR + "kenney/doorOpen_000.ogg", Vector3.ZERO, -4.0, 0.05)


func scan(pos: Vector3) -> void:
	play_at(DIR + "kenney/switch_002.ogg", pos, -4.0, 0.15)

func frenzy_stinger() -> void:
	play_ui(DIR + "kenney/lowFrequency_explosion_001.ogg", -2.0)
	play_ui(DIR + "kenney/error_004.ogg", -4.0)
