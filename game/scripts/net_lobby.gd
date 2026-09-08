extends CanvasLayer
## NetLobby — in-world co-op panel, Minecraft "Open to LAN" style.
## You keep playing solo; flip the switch whenever you want the squad in:
##   F5 = host (UDP 24565, UPnP best-effort), F6 = join the IP in the box.
## The host's world seed is sent to every joiner, so everyone rebuilds an
## identical procedural city; from then on the host is the authority.

var panel: PanelContainer
var status: Label
var ip_edit: LineEdit
var last_ip := "127.0.0.1"

func _ready() -> void:
	layer = 92
	_build_ui()
	Net.lobby_changed.connect(_refresh)
	Net.peer_joined.connect(_on_peer_signal)
	Net.peer_left.connect(_on_peer_signal)
	Net.join_failed.connect(_on_join_failed)
	Net.seed_received.connect(_on_seed_received)
	_refresh()

func _build_ui() -> void:
	panel = PanelContainer.new()
	panel.name = "NetLobbyPanel"
	add_child(panel)
	panel.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	panel.offset_left = 12
	panel.offset_top = -132
	panel.offset_right = 372
	panel.offset_bottom = -12
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	panel.add_child(box)
	var title := Label.new()
	title.text = "CO-OP 联机   (F5 开房 / F6 加入)"
	title.add_theme_font_size_override("font_size", 15)
	box.add_child(title)
	status = Label.new()
	status.text = "单机模式"
	status.add_theme_font_size_override("font_size", 13)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(status)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 6)
	box.add_child(row)
	var host_btn := Button.new()
	host_btn.text = "开房 HOST (F5)"
	host_btn.pressed.connect(_on_host_pressed)
	row.add_child(host_btn)
	var join_btn := Button.new()
	join_btn.text = "加入 JOIN (F6)"
	join_btn.pressed.connect(_on_join_pressed)
	row.add_child(join_btn)
	var leave_btn := Button.new()
	leave_btn.text = "断开"
	leave_btn.pressed.connect(_on_leave_pressed)
	row.add_child(leave_btn)
	ip_edit = LineEdit.new()
	ip_edit.placeholder_text = "主机 IP，如 192.168.10.165"
	ip_edit.text_changed.connect(func(t: String): last_ip = t.strip_edges())
	box.add_child(ip_edit)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_F5:
			_on_host_pressed()
		elif event.physical_keycode == KEY_F6:
			_on_join_pressed()

func _on_host_pressed() -> void:
	if Net.online:
		return
	if Net.host_game():
		_refresh()
	else:
		status.text = "开房失败：端口 %d 被占用？" % Net.PORT

func _on_join_pressed() -> void:
	if Net.online:
		return
	var ip := ip_edit.text.strip_edges()
	if ip.is_empty():
		ip = last_ip
	if ip.is_empty():
		status.text = "先填主机 IP 再加入"
		return
	last_ip = ip
	if Net.join_game(ip):
		status.text = "正在连接 %s ..." % ip
	else:
		status.text = "无法发起连接"

func _on_leave_pressed() -> void:
	Net.leave()
	_refresh()

func _on_peer_signal(_pid: int) -> void:
	_refresh()

func _on_join_failed(reason: String) -> void:
	status.text = "加入失败：%s" % reason

func _on_seed_received() -> void:
	status.text = "已收到世界种子 — 重建地图中..."

func _refresh() -> void:
	if not Net.online:
		status.text = "单机模式 — 主机需开放 UDP %d，或加入别人的房" % Net.PORT
	elif Net.hosting:
		var n := multiplayer.get_peers().size()
		status.text = "主机运行中 :%d · 玩家 %d/%d · 队友死亡=团灭" % [Net.PORT, n + 1, Net.MAX_PEERS + 1]
	elif Net.pending_seed >= 0:
		status.text = "已连接 — 世界同步中..."
	else:
		status.text = "已连接 (ID %d) — 等待主机发送世界种子..." % Net.my_id()
