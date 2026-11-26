"""规范化全部人物与家族文件中的引文：
- 正文：独用段落写原文全文＋出处链接；共享段落写定位符链接（见 scripts/bodyline.py）。
  是否共享按全部文件统计，所以每次都处理全部文件。
- YAML：定位符保持纯文本，按当前规则重算最短锚点。
用法: python3 scripts/reanchor.py
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from refs import resolve, make, _paras, REF
from bodyline import parse_line, format_line, citation_map, all_files


def short(loc):
    t, meta = resolve(loc)
    pn = meta["para"]
    lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
    return make(meta["book"], meta["juan"], pn, "".join(_paras(meta["name"], meta["juan"])[lo - 1:hi]), t)


def process(path: Path, cm):
    _, head, body = path.read_text(encoding="utf-8").split("---\n", 2)
    hl = []
    for line in head.split("\n"):
        m = re.match(r"^(\s*-\s+|\s*[^:\s][^:]*:\s+)(.+)$", line)
        if m and REF.match(m[2].strip()):
            line = m[1] + short(m[2].strip())
        hl.append(line)
    bl = []
    for line in body.split("\n"):
        r = parse_line(line)
        bl.append(format_line(path, r[0], cm) if r else line)
    path.write_text("---\n" + "\n".join(hl) + "---\n" + "\n".join(bl), encoding="utf-8")


if __name__ == "__main__":
    files = all_files()
    cm = citation_map(files)
    for f in files:
        process(f, cm)
    print(f"规范化 {len(files)} 个文件")
