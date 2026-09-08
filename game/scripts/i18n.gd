extends RefCounted
## 极简 i18n —— 只做中/英两档, 按系统 locale 自动选, 缺词回退英文。
## 用法: const I18n := preload("res://game/scripts/i18n.gd") ; I18n.t("ammo")

const ZH := {
	"hp": "生命",
	"loot": "战利品",
	"stash": "库存",
	"quota": "配额",
	"kills": "击杀",
	"extracting": "撤离中…",
	"ammo": "弹药",
	"click_to_lock": "点击画面锁定鼠标",
	"click_to_resume": "点击画面继续",
	"tutorial_title": "操作指南",
	"dismiss": "按任意键 / 点击开始",
	"ammo_gained": "弹药 +%d",
	"raid_start": "突袭开始 — 搜刮城市，去绿色光束撤离",
	"died": "你死了 — 随身战利品丢失",
	"spitter_warning": "黑暗中有什么在吐酸…",
	"hint_move": "移动",
	"hint_sprint": "冲刺",
	"hint_crouch": "下蹲",
	"hint_jump": "跳跃",
	"hint_shoot": "射击",
	"hint_aim": "瞄准",
	"hint_reload": "换弹",
	"hint_interact": "拾取 / 交互",
	"hint_scan": "扫描战利品",
	"hint_flashlight": "手电",
	"hint_view": "第一/第三人称",
	"key_wasd": "W A S D",
	"key_shift": "Shift",
	"key_ctrl": "Ctrl",
	"key_space": "Space",
	"key_lmb": "鼠标左键",
	"key_rmb": "鼠标右键",
	"key_mmb": "鼠标中键",
	"key_r": "R",
	"key_e": "E",
	"key_t": "T",
	"key_v": "V",
}

const EN := {
	"hp": "HP",
	"loot": "LOOT",
	"stash": "STASH",
	"quota": "QUOTA",
	"kills": "KILLS",
	"extracting": "EXTRACTING…",
	"ammo": "AMMO",
	"click_to_lock": "Click to lock mouse",
	"click_to_resume": "Click to resume",
	"tutorial_title": "CONTROLS",
	"dismiss": "Press any key / click to start",
	"ammo_gained": "Ammo +%d",
	"hint_move": "Move",
	"hint_sprint": "Sprint",
	"hint_crouch": "Crouch",
	"hint_jump": "Jump",
	"hint_shoot": "Shoot",
	"hint_aim": "Aim",
	"hint_reload": "Reload",
	"hint_interact": "Pick up / Interact",
	"hint_scan": "Scan loot",
	"hint_flashlight": "Flashlight",
	"hint_view": "First / third person",
	"key_wasd": "W A S D",
	"key_shift": "Shift",
	"key_ctrl": "Ctrl",
	"key_space": "Space",
	"key_lmb": "LMB",
	"key_rmb": "RMB",
	"key_mmb": "MMB",
	"key_r": "R",
	"key_e": "E",
	"key_t": "T",
	"key_v": "V",
}


static func is_zh() -> bool:
	return OS.get_locale().begins_with("zh")


static func t(key: String) -> String:
	var table: Dictionary = ZH if is_zh() else EN
	return String(table.get(key, EN.get(key, key)))
