extends "res://game/scripts/net_transport.gd"
## ENet implementation of NetTransport — the current built-in LAN path
## (UDP :24565, Minecraft "Open to LAN" equivalent). Behavior-identical
## to what used to be inlined in net.gd host_game/join_game/leave.

var _peer: ENetMultiplayerPeer

func start_host(port: int, max_peers: int) -> Error:
	_peer = ENetMultiplayerPeer.new()
	return _peer.create_server(port, max_peers)

func join(address: String, port: int) -> Error:
	_peer = ENetMultiplayerPeer.new()
	return _peer.create_client(address, port)

func close() -> void:
	if _peer != null:
		_peer.close()
	_peer = null

func attach(node: Node) -> void:
	node.multiplayer.multiplayer_peer = _peer
