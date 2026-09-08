"""暗色基地营地预览(带入口)。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_vendor_previews import render_basecamp

render_basecamp("base_camp_dark.glb", "composite_basecamp_dark.png")
