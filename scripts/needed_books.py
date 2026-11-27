"""列出构建网站/校验所需的书：已用书目 + 所有定位符引用到的书（供 fetch_sources.sh 使用）。"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT, load_books
B = load_books()
need = set((ROOT / "scripts" / "used_books.txt").read_text(encoding="utf-8").split())
pat = re.compile(r"([^\s>\[\-“”‘’|｜·]+)·\d+[^·｜\s\]]*·\d+(?:-\d+)?(?:｜|\])")
for d in ("人物", "家族"):
    for f in (ROOT / d).rglob("*.md"):
        for m in pat.finditer(f.read_text(encoding="utf-8")):
            if m[1] in B:
                need.add(B[m[1]]["name"])
order = [l.split("\t")[0] for l in (ROOT / "scripts" / "dibens.tsv").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
print(" ".join(b for b in order if b in need))
