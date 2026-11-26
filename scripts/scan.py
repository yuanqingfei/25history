"""全史扫描：为一个人物检索其首见书之后的全部史书（已在“已查”中的书除外），按句列出命中。
- 检索词：姓名 + 别称（YAML 中“检索词”字段可覆盖；“检索排除”为正则列表，命中处前后文匹配即剔除）。
- 输出每处命中所在的整句及定位符，供逐条判断：本人 / 同名异人 / 字面误中。
用法: python3 scripts/scan.py 人物/史记/纪信.md [--all]   （--all 连“已查”的书也扫）
"""
import argparse, re, sys, yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT, juan_list

ORDER = [l.split("\t")[0] for l in (ROOT / "scripts" / "dibens.tsv").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
SENT = re.compile(r"[^。！？]*[。！？”’]*")


def sentence(p, i, j):
    a = max(p.rfind("。", 0, i), p.rfind("！", 0, i), p.rfind("？", 0, i)) + 1
    ends = [k for k in (p.find("。", j), p.find("！", j), p.find("？", j)) if k >= 0]
    b = (min(ends) + 1) if ends else len(p)
    while b < len(p) and p[b] in "”’）":
        b += 1
    return a, b


def scan(path, include_checked=False):
    meta = yaml.safe_load(path.read_text(encoding="utf-8").split("---\n", 2)[1])
    first = path.parent.name
    terms = meta.get("检索词") or [meta["姓名"]] + [a for a in (meta.get("别称") or []) if len(a) >= 2]
    excl = [re.compile(x) for x in (meta.get("检索排除") or [])]
    done = set(meta.get("已查") or []) if not include_checked else {first}
    books = [b for b in ORDER[ORDER.index(first):] if b not in done]
    pat = re.compile("|".join(map(re.escape, sorted(set(terms), key=len, reverse=True))))
    hits, dropped = [], 0
    for b in books:
        for j, title, paras in juan_list(b):
            for pn, p in enumerate(paras, 1):
                for m in pat.finditer(p):
                    ctx = p[max(0, m.start() - 6):m.end() + 6]
                    if any(x.search(ctx) for x in excl):
                        dropped += 1; continue
                    a, e = sentence(p, m.start(), m.end())
                    text, loc_pn = p[a:e], str(pn)
                    if e == len(p) and p and p[-1] not in "。！？”’）" and pn < len(paras):
                        nxt = paras[pn]                       # 底本误断段：句子接到下一段
                        k = min([x for x in (nxt.find("。"), nxt.find("！"), nxt.find("？")) if x >= 0] or [len(nxt) - 1])
                        text, loc_pn = text + nxt[:k + 1], f"{pn}-{pn + 1}"
                    hits.append((b, j, loc_pn, title, text.lstrip("”’")))
    # 同一句多次命中只留一次
    seen, out = set(), []
    for h in hits:
        if h[:3] + (h[4],) not in seen:
            seen.add(h[:3] + (h[4],)); out.append(h)
    return books, out, dropped


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("file"); ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    books, hits, dropped = scan(Path(a.file), a.all)
    print(f"扫描 {len(books)} 部，命中 {len(hits)} 句，按排除规则剔除 {dropped} 处")
    for b, j, pn, title, s in hits:
        print(f"{b}·{j}·{pn}｜{s}　〔{title}〕")  # 可直接复制为定位符
