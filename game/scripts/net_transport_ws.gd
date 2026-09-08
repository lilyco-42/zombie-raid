extends RefCounted
## WsTransport — raw WebSocketPeer link to the Rust dedicated server
## (docs/SERVER_DEV.md §6 step ③). NOT a MultiplayerAPI peer: net.gd flips
## to _ws_mode and routes JSON dicts through send_text / poll_texts, so
## this class deliberately does not extend net_transport.gd (its join()
## takes a full ws:// URL, not address+port).

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

## Pump the socket state machine and drain every queued text frame.
## Returns the lines received since the previous call.
func poll_texts() -> PackedStringArray:
	var out := PackedStringArray()
	if _ws == null:
		return out
	_ws.poll()
	if _ws.get_ready_state() == WebSocketPeer.STATE_OPEN:
		while _ws.get_available_packet_count() > 0:
			out.append(_ws.get_packet().get_string_from_utf8())
	return out
