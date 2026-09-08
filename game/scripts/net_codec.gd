extends RefCounted
## NetCodec — GDScript side of the binary wire format v2
## (docs/SERVER_DEV.md §"Binary frame format"). Produces/consumes exactly
## the bincode legacy layout the Rust protocol crate pins in its
## golden-byte tests: little-endian, u32 enum discriminants, u64 vec
## lengths, 1-byte bools, 4-byte f32s, no struct padding.
##
## Dictionaries going IN are the same shapes net.gd builds for the JSON
## path; the dictionary coming OUT has the same shape JSON.parse_string
## would produce — so _ws_send / _dispatch_s2c need zero changes. Unit
## variants decode to {Name: null}, matching the serde JSON map form.

# C2S variant indices = declaration order in protocol::C2S
const C2S_HELLO := 0
const C2S_PLAYER_STATE := 1
const C2S_HIT_ZOMBIE := 2
const C2S_BOX_TAKEN := 3
const C2S_REPORT_EXTRACT := 4
const C2S_REPORT_PLAYER_DIED := 5
const C2S_BUY_ITEM := 6
const C2S_REQUEST_SHOP := 7

# S2C variant indices = declaration order in protocol::S2C
const S2C_SEED := 0
const S2C_ZOMBIE_STATES := 1
const S2C_NET_STATE := 2
const S2C_RAID_STARTED := 3
const S2C_ZOMBIE_DEAD := 4
const S2C_REMOVE_BOX := 5
const S2C_EXTRACT_SUCCESS := 6
const S2C_RAID_FAILED := 7
const S2C_DAMAGE_PLAYER := 8
const S2C_SHOP_LIST := 9
const S2C_INVENTORY_UPDATE := 10
const S2C_TRADE_ERROR := 11

# ZombieEnt wire size: u32 id + 3×f32 pos + f32 yaw + u8 anim + u8 ztype
const ENT_SIZE := 22


# ============================================================== encode ===

static func _buf() -> StreamPeerBuffer:
	var b := StreamPeerBuffer.new()
	b.big_endian = false  # bincode legacy is little-endian
	return b


## Encode a client->server message dict (same shape as the JSON path
## builds) into bincode bytes. Unknown variants return empty — a bug, not
## a runtime event (mirrors the Rust side's infallibility).
static func encode_c2s(msg: Dictionary) -> PackedByteArray:
	for variant in msg:
		match String(variant):
			"Hello":
				return _enc_hello(msg[variant])
			"PlayerState":
				return _enc_player_state(msg[variant])
			"HitZombie":
				return _enc_hit_zombie(msg[variant])
			"BoxTaken":
				return _enc_box_taken(msg[variant])
			"ReportExtract":
				return _enc_report_extract(msg[variant])
			"ReportPlayerDied":
				var b := _buf()
				b.put_u32(C2S_REPORT_PLAYER_DIED)
				return b.data_array
			"BuyItem":
				return _enc_buy_item(msg[variant])
			"RequestShop":
				return _enc_request_shop()
	push_error("[netcodec] unknown C2S variant in %s" % [msg])
	return PackedByteArray()


static func _enc_hello(d: Dictionary) -> PackedByteArray:
	var b := _buf()
	b.put_u32(C2S_HELLO)
	b.put_u32(int(d["ver"]))
	return b.data_array


static func _enc_player_state(d: Dictionary) -> PackedByteArray:
	var b := _buf()
	b.put_u32(C2S_PLAYER_STATE)
	b.put_u32(int(d["pid"]))
	for v in d["pos"]:
		b.put_float(float(v))
	b.put_float(float(d["yaw"]))
	b.put_float(float(d["speed"]))
	b.put_8(1 if bool(d["on_floor"]) else 0)
	b.put_8(1 if bool(d["crouch"]) else 0)
	return b.data_array


static func _enc_hit_zombie(d: Dictionary) -> PackedByteArray:
	var b := _buf()
	b.put_u32(C2S_HIT_ZOMBIE)
	b.put_u32(int(d["pid"]))
	b.put_u32(int(d["net_id"]))
	b.put_float(float(d["dmg"]))
	return b.data_array


static func _enc_box_taken(d: Dictionary) -> PackedByteArray:
	var b := _buf()
	b.put_u32(C2S_BOX_TAKEN)
	for v in d["pos"]:
		b.put_float(float(v))
	return b.data_array


static func _enc_report_extract(d: Dictionary) -> PackedByteArray:
	var b := _buf()
	b.put_u32(C2S_REPORT_EXTRACT)
	b.put_8(1 if bool(d["in_zone"]) else 0)
	return b.data_array


static func _enc_buy_item(d: Dictionary) -> PackedByteArray:
	var b := _buf()
	b.put_u32(C2S_BUY_ITEM)
	b.put_u32(int(d["pid"]))
	_put_str(b, String(d["item_id"]))
	return b.data_array


static func _enc_request_shop() -> PackedByteArray:
	var b := _buf()
	b.put_u32(C2S_REQUEST_SHOP)
	return b.data_array


## bincode legacy strings: u64 little-endian length + raw UTF-8 bytes
## (StreamPeer's own put_utf8_string uses a u16 prefix - do NOT use it).
static func _put_str(b: StreamPeerBuffer, s: String) -> void:
	var bytes := s.to_utf8_buffer()
	b.put_u64(bytes.size())
	b.put_data(bytes)


# ============================================================== decode ===

static func _rbuf(bytes: PackedByteArray) -> StreamPeerBuffer:
	var b := _buf()
	b.data_array = bytes
	return b


## Decode a server->client bincode frame into the same dictionary shape
## JSON.parse_string would yield for the map form (unit variants become
## {Name: null}). Malformed frames return {} — callers skip empties.
static func decode_s2c(bytes: PackedByteArray) -> Dictionary:
	var b := _rbuf(bytes)
	if b.get_available_bytes() < 4:
		return {}
	match int(b.get_u32()):
		S2C_SEED:
			return _dec_seed(b)
		S2C_ZOMBIE_STATES:
			return _dec_zombie_states(b)
		S2C_NET_STATE:
			return _dec_net_state(b)
		S2C_RAID_STARTED:
			return {"RaidStarted": null}
		S2C_ZOMBIE_DEAD:
			return _dec_zombie_dead(b)
		S2C_REMOVE_BOX:
			return _dec_remove_box(b)
		S2C_EXTRACT_SUCCESS:
			return {"ExtractSuccess": null}
		S2C_RAID_FAILED:
			return {"RaidFailed": null}
		S2C_DAMAGE_PLAYER:
			return _dec_damage_player(b)
		S2C_SHOP_LIST:
			return _dec_shop_list(b)
		S2C_INVENTORY_UPDATE:
			return _dec_inventory_update(b)
		S2C_TRADE_ERROR:
			return _dec_trade_error(b)
	return {}


static func _dec_seed(b: StreamPeerBuffer) -> Dictionary:
	if b.get_available_bytes() < 12:
		return {}
	var seed := int(b.get_u64())
	var elapsed := b.get_float()
	return {"Seed": {"seed": seed, "elapsed": elapsed}}


static func _dec_zombie_states(b: StreamPeerBuffer) -> Dictionary:
	if b.get_available_bytes() < 12:
		return {}
	var seq := int(b.get_u32())
	var n := int(b.get_u64())
	if n > 4096:  # corrupted length guard
		return {}
	var ents: Array = []
	for i in n:
		if b.get_available_bytes() < ENT_SIZE:
			return {}
		var id := int(b.get_u32())
		var x := b.get_float()
		var y := b.get_float()
		var z := b.get_float()
		var yaw := b.get_float()
		var anim := int(b.get_8())
		var ztype := int(b.get_8())
		ents.append({"id": id, "pos": [x, y, z], "yaw": yaw, "anim": anim, "ztype": ztype})
	return {"ZombieStates": {"seq": seq, "ents": ents}}


static func _dec_net_state(b: StreamPeerBuffer) -> Dictionary:
	if b.get_available_bytes() < 5:
		return {}
	var elapsed := b.get_float()
	var frenzy := bool(b.get_8())
	return {"NetState": {"elapsed": elapsed, "frenzy": frenzy}}


static func _dec_zombie_dead(b: StreamPeerBuffer) -> Dictionary:
	if b.get_available_bytes() < 20:
		return {}
	var net_id := int(b.get_u32())
	var x := b.get_float()
	var y := b.get_float()
	var z := b.get_float()
	var drop := int(b.get_u32())
	if drop >= 0x80000000:  # i32 -> GDScript int (two's complement)
		drop -= 0x100000000
	return {"ZombieDead": {"net_id": net_id, "pos": [x, y, z], "drop_value": drop}}


static func _dec_remove_box(b: StreamPeerBuffer) -> Dictionary:
	if b.get_available_bytes() < 12:
		return {}
	var x := b.get_float()
	var y := b.get_float()
	var z := b.get_float()
	return {"RemoveBox": {"pos": [x, y, z]}}


static func _dec_damage_player(b: StreamPeerBuffer) -> Dictionary:
	if b.get_available_bytes() < 8:
		return {}
	var pid := int(b.get_u32())
	var dmg := b.get_float()
	return {"DamagePlayer": {"pid": pid, "dmg": dmg}}


## bincode legacy string reader - see _put_str; "" means a corrupted frame.
static func _get_str(b: StreamPeerBuffer) -> String:
	var n := int(b.get_u64())
	if n > 4096:  # corrupted length guard
		return ""
	return b.get_data(n)[1].get_string_from_utf8()


static func _dec_shop_list(b: StreamPeerBuffer) -> Dictionary:
	if b.get_available_bytes() < 8:
		return {}
	var n := int(b.get_u64())
	if n > 4096:
		return {}
	var entries: Array = []
	for i in n:
		if b.get_available_bytes() < 9:
			return {}
		var id := _get_str(b)
		if id == "":
			return {}
		entries.append([id, int(b.get_u32())])
	return {"ShopList": {"entries": entries}}


static func _dec_inventory_update(b: StreamPeerBuffer) -> Dictionary:
	if b.get_available_bytes() < 20:
		return {}
	var pid := int(b.get_u32())
	var item_id := _get_str(b)
	if item_id == "":
		return {}
	var count := int(b.get_u64())
	if count > 0x7fffffffffffffff:  # i64 raw -> GDScript int (two's complement)
		count -= 0x10000000000000000
	return {"InventoryUpdate": {"pid": pid, "item_id": item_id, "count": count}}


static func _dec_trade_error(b: StreamPeerBuffer) -> Dictionary:
	if b.get_available_bytes() < 8:
		return {}
	var pid := int(b.get_u32())
	var reason := _get_str(b)
	if reason == "":
		return {}
	return {"TradeError": {"pid": pid, "reason": reason}}
