"""太空基地件压暗变体: 与基地营地/地牢冷调统一, 输出到 static/vendor/space_dark/。"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_vendor_lc import SPACE_PICKS, SPACE_DIR
from build_vendor_batch2 import curate_batch

# 比地牢件更暗一档, 贴近 LC 月面设施 mood
DARK_SAT, DARK_TINT = 0.35, (0.52, 0.55, 0.64)

if __name__ == "__main__":
    n, missing = curate_batch(SPACE_DIR, SPACE_PICKS, "space_dark", DARK_SAT, DARK_TINT)
    print(f"SPACE_DARK_DONE n={n}")
    if missing:
        print("MISSING:", missing)
