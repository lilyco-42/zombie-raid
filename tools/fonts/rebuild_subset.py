"""重生成 UI 中文字体子集 (往 i18n.gd 加了新文案后重跑一次)。

用法:
  1) 下载完整字体 (15.7MB, 一次性):
     curl -L -o /tmp/NotoSansCJKsc-Regular.otf \
       https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf
  2) python tools/fonts/rebuild_subset.py /tmp/NotoSansCJKsc-Regular.otf
     -> assets/fonts/noto_sc_subset.otf (28KB, 230 字形)
依赖: pip install --target <dir> fonttools  (见 memory Round 41)
"""
import os, string, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = sys.argv[1] if len(sys.argv) > 1 else "/tmp/NotoSansCJKsc-Regular.otf"
OUT = os.path.join(ROOT, "assets", "fonts", "noto_sc_subset.otf")


def glyph_text() -> str:
    """扫 game/scripts 下所有 .gd 的字符串字面量 (跳过注释), 新文案自动收录。"""
    import glob, re
    chars = set()
    for path in glob.glob(os.path.join(ROOT, "game", "scripts", "*.gd")):
        src = open(path, encoding="utf-8").read()
        for lit in re.findall(r'"((?:[^"\\]|\\.)*)"', src):
            chars |= set(lit)
    chars |= set(string.printable)
    chars |= set("，。：；！？—…·、（）《》「」『』“”‘’％＋×－￥")
    chars -= set("\n\r\t")
    return "".join(sorted(chars))


def main() -> None:
    txt = os.path.join(os.path.dirname(__file__), "glyphs.txt")
    with open(txt, "w", encoding="utf-8") as fh:
        fh.write(glyph_text())
    subprocess.run([
        sys.executable, "-m", "fontTools.subset", SRC,
        f"--text-file={txt}", f"--output-file={OUT}",
        "--no-hinting", "--desubroutinize", "--name-IDs=0,1,2,3",
        "--layout-features=",
    ], check=True)
    print("subset ->", OUT, os.path.getsize(OUT), "bytes")


main()
