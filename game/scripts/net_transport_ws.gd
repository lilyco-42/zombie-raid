extends RefCounted
## WsTransport — raw WebSocketPeer link to the Rust dedicated server
## (docs/SERVER_DEV.md §6 step ③). NOT a MultiplayerAPI peer: net.gd flips
## to _ws_mode and routes frames through send_text / send_bytes /
## poll_frames, so this class deliberately does not extend
## net_transport.gd (its join() takes a full ws:// URL, not address+port).
## Text frames carry JSON (v1), binary frames carry bincode (v2); the
## caller tells them apart by the element type poll_frames returns.

var _ws: WebSocketPeer = null

func start_host(_port: int, _max_peers: int) -> Error:
	## The dedicated server never runs inside Godot in WS mode.
	return ERR_UNAVAILABLE

func join(url: String) -> Error:
	_ws = WebSocketPeer.new()
	var err := _ws.connect_to_url(url)
	if err != OK:
		_ws = null
	return err

func close() -> void:
	if _ws != null:
		_ws.close()
	_ws = null

func attach(_node: Node) -> void:
	pass  # no MultiplayerAPI in WS mode; net.gd pumps and dispatches manually

func is_open() -> bool:
	return _ws != null and _ws.get_ready_state() == WebSocketPeer.STATE_OPEN

func is_closed() -> bool:
	return _ws == null or _ws.get_ready_state() == WebSocketPeer.STATE_CLOSED

func send_text(line: String) -> void:
	if is_open():
		_ws.send_text(line)

func send_bytes(data: PackedByteArray) -> void:
	if is_open():
		_ws.send(data)  # binary frame (Godot 4.4+ unified WebSocket API)

## Pump the socket state machine and drain every queued frame. String
## elements are text frames (JSON), PackedByteArray elements are binary
## frames (bincode v2 — decode with net_codec.gd).
func poll_frames() -> Array:
	var out := []
	if _ws == null:
		return out
	_ws.poll()
	if _ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		while _ws.get_available_packet_count() > 0:
			var pkt := _ws.get_packet()
			if _ws.was_string_packet():
				out.append(pkt.get_string_from_utf8())
			else:
				out.append(pkt)
	return out
