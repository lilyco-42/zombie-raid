extends RefCounted
## NetTransport — swappable link-layer under net.gd.
## Step ① of docs/SERVER_DEV.md §6: the connection lifecycle lives behind
## this interface so the ENet LAN path and the future WS/Rust-server path
## are interchangeable without touching any rpc_* call site.
##
## Contract:
##   start_host() / join()  → Error (OK on success)
##   attach(node)           → wire the underlying MultiplayerPeer into the
##                            SceneTree multiplayer root (rpc_* keeps working)
##   close()                → tear down; the transport is unusable afterwards

func start_host(_port: int, _max_peers: int) -> Error:
	return ERR_UNAVAILABLE

func join(_address: String, _port: int) -> Error:
	return ERR_UNAVAILABLE

func close() -> void:
	pass

func attach(_node: Node) -> void:
	pass
