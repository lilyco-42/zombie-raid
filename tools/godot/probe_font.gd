extends Node3D
## 字体渲染探针: 验证项目自定义字体(中文)真的画出来了。

func _ready() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	layer.add_child(root)
	var bg := ColorRect.new()
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.color = Color(0.08, 0.08, 0.1)
	root.add_child(bg)
	var label := Label.new()
	label.text = "弹药 12 / 120  生命 100  撤离中…  操作指南\nW A S D 移动 | R 换弹 | T 手电 | V 视角"
	label.set_anchors_preset(Control.PRESET_CENTER)
	label.offset_left = -400
	label.offset_right = 400
	label.offset_top = -60
	label.offset_bottom = 60
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 30)
	root.add_child(label)
	await get_tree().create_timer(1.0).timeout
	var img := get_viewport().get_texture().get_image()
	img.save_png("res://assets/_previews/font_check.png")
	print("FONT_PROBE saved")
	get_tree().quit()
