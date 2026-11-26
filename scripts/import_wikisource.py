"""把 底本/维基文库/<維基書名>/ 导入为 sources/<书名>/NNN.md。
- 去掉每卷开头的导航行（含“｜”的表格行、箭头等）。
- --only 起-止：只导入这些卷号，并且不清空目标目录（用于给 TLS 主底本补缺卷）。
- 在 sources/<书名>/来源.tsv 中记录每个卷文件的来源。
用法: python3 scripts/import_wikisource.py <維基書名> <书名> [--only 191-200]
"""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT, SOURCES

ap = argparse.ArgumentParser()
ap.add_argument("wiki"); ap.add_argument("book"); ap.add_argument("--only", default="")
a = ap.parse_args()
src = ROOT / "底本" / "维基文库" / a.wiki
out = SOURCES / a.book
lo, hi = map(int, a.only.split("-")) if a.only else (None, None)
if lo is None:
    if out.exists():
        for f in out.glob("*"):
            f.unlink()
out.mkdir(parents=True, exist_ok=True)
rev = {}
mf = src / "manifest.tsv"
for ln in mf.read_text(encoding="utf-8").splitlines() if mf.exists() else []:
    c = ln.split("\t")
    rev[c[1]] = (c[2], c[4])          # 卷标记 → (revid, url)；后写的覆盖先写的
NAV = re.compile(r"｜|^[←→]|^上一卷|^下一卷")
n = 0
rows = []
for f in sorted(src.glob("[0-9]*.md")):
    num = int(f.stem[:3])
    if lo is not None and not (lo <= num <= hi):
        continue
    lines = f.read_text(encoding="utf-8").split("\n")
    title = lines[0].lstrip("# ").strip()
    paras = [l.strip() for l in lines[1:] if l.strip()]
    while paras and NAV.search(paras[0]):
        paras.pop(0)
    (out / f.name).write_text(f"# {title}\n\n" + "\n\n".join(paras) + "\n", encoding="utf-8")
    rid, url = rev.get(f.stem, ("", ""))
    rows.append(f"{f.stem}\t维基文库\t{url}\trevid={rid}")
    n += 1
with open(out / "来源.tsv", "a", encoding="utf-8") as fh:
    fh.write("".join(r + "\n" for r in rows))
print(f"{a.book}：从维基文库导入 {n} 卷" + (f"（卷{lo}—{hi}，补入 TLS 缺卷）" if lo else ""))
