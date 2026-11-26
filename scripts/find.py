"""在一部史书中检索人名（可多个别称），列出每处出现所在的卷、段落及上下文。
用法: python3 scripts/find.py 史记 范增 亞父 [--ctx 60] [--exclude 卷号,卷号]
"""
import argparse, re, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from corpus import juan_list

ap = argparse.ArgumentParser()
ap.add_argument("book"); ap.add_argument("names", nargs="+")
ap.add_argument("--ctx", type=int, default=60)
ap.add_argument("--exclude", default="")
a = ap.parse_args()
ex = {int(x) for x in a.exclude.split(",") if x}
pat = re.compile("|".join(map(re.escape, a.names)))
total = 0
for n, title, text in juan_list(a.book):
    if n in ex:
        continue
    for pi, para in enumerate(text.split("\n")):
        for m in pat.finditer(para):
            s, e = max(0, m.start() - a.ctx), min(len(para), m.end() + a.ctx)
            print(f"[{n:03d} {title} ¶{pi}] …{para[s:e]}…")
            total += 1
print(f"共 {total} 处", file=sys.stderr)
