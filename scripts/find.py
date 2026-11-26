"""在一部或多部史书中检索人名，列出每处出现的定位（書·卷·段）与上下文。
人名按繁体输入即可，检索简体底本时自动转换。
用法: python3 scripts/find.py 史记,汉书 范增 亞父 [--ctx 60] [--exclude 7,8]
      python3 scripts/find.py 史记+ 范增     # 本书 + neighbors.tsv 中的全部相邻史书
"""
import argparse, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import juan_list, load_books
import opencc
T2S, S2T = opencc.OpenCC("t2s"), opencc.OpenCC("s2t")
ap = argparse.ArgumentParser()
ap.add_argument("books"); ap.add_argument("names", nargs="+")
ap.add_argument("--ctx", type=int, default=60); ap.add_argument("--exclude", default="")
a = ap.parse_args()
ex = set(filter(None, a.exclude.split(",")))
B = load_books(); total = 0
NB = {}
for ln in (Path(__file__).parent / "neighbors.tsv").read_text(encoding="utf-8").splitlines():
    if ln and not ln.startswith("#"):
        c = ln.split("\t"); NB[c[0]] = c[1].split(",")
books = []
for bk in a.books.split(","):
    if bk.endswith("+"):
        bk = B[bk[:-1]]["name"]; books += [bk] + NB.get(bk, [])
    else:
        books.append(bk)
for bk in books:
    if not (Path(__file__).parent.parent / "sources" / B[bk]["name"]).exists():
        print(f"！{bk} 底本尚未获取，跳过", file=sys.stderr); continue
    info = B[bk]
    names = set(a.names) | {T2S.convert(n) for n in a.names} | {S2T.convert(n) for n in a.names}
    pat = re.compile("|".join(map(re.escape, sorted(names, key=len, reverse=True))))
    for j, title, paras in juan_list(info["name"]):
        if j in ex and bk == books[0]:
            continue
        for pn, p in enumerate(paras, 1):
            for m in pat.finditer(p):
                s, e = max(0, m.start() - a.ctx), min(len(p), m.end() + a.ctx)
                print(f"{info['name']}·{j}·{pn} 〔{title}〕 …{p[s:e]}…"); total += 1
print(f"共 {total} 处", file=sys.stderr)
