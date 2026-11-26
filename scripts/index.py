"""生成 索引/段落人物.tsv：每个被引用的段落涉及哪些人物（共享段落的反向索引）。"""
import sys, collections, yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT
from refs import parse

idx = collections.defaultdict(set)
for f in sorted((ROOT / "人物").rglob("*.md")):
    if f.name.startswith("_"):
        continue
    _, head, body = f.read_text(encoding="utf-8").split("---\n", 2)
    meta = yaml.safe_load(head)
    for line in body.splitlines():
        if line.startswith(">"):
            info, juan, pn, _ = parse(line[1:].strip())
            idx[(info["fan"], juan, pn)].add(f"{meta['id']} {meta['姓名']}")
def key(k):
    import re
    m = re.match(r"(\d+)(.*)", k[1]); return (k[0], int(m[1]), m[2], k[2])
rows = ["书\t卷\t段\t人数\t人物"] + [f"{b}\t{j}\t{p}\t{len(v)}\t{'、'.join(sorted(v))}" for (b, j, p), v in sorted(idx.items(), key=lambda kv: key(kv[0]))]
(ROOT / "索引").mkdir(exist_ok=True)
(ROOT / "索引" / "段落人物.tsv").write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"{len(idx)} 个段落，其中被多人共享 {sum(1 for v in idx.values() if len(v) > 1)} 个")
