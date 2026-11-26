"""把传记中的定位符展开成可读的全文传记，输出到 build/（不入库）。
用法: python3 scripts/render.py [文件 ...]   默认渲染 人物/ 下全部
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT, juan_list
from refs import resolve
from bodyline import parse_line

TITLES = {}
def title(name, juan):
    if (name, juan) not in TITLES:
        for j, t, _ in juan_list(name):
            TITLES[(name, j)] = t
    return TITLES.get((name, juan), "")

def render(path: Path) -> str:
    _, head, body = path.read_text(encoding="utf-8").split("---\n", 2)
    out = []
    for line in body.splitlines():
        s = line.strip()
        if s.startswith(">"):
            text, m = resolve(parse_line(s)[0])
            out.append(f"{text}〔{m['book']}·卷{m['juan']}·{title(m['name'], m['juan'])}〕")
        else:
            out.append(line)
    return "\n".join(out).strip() + "\n"

files = [Path(a) for a in sys.argv[1:]] or sorted(p for p in (ROOT / "人物").rglob("*.md") if not p.name.startswith("_"))
for f in files:
    o = ROOT / "build" / f.relative_to(ROOT)
    o.parent.mkdir(parents=True, exist_ok=True)
    o.write_text(render(f), encoding="utf-8")
print(f"渲染 {len(files)} 篇 → build/")
