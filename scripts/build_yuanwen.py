"""生成 原文/<書名>/<NNN>.md：底本的可浏览版本，每段带锚点 #pN，供传记中的定位符链接跳转。
每段后列出引用该段的人物（反向链接）。只生成被引用到的书（或用参数指定）。
用法: python3 scripts/build_yuanwen.py [书名 ...]
"""
import re, sys, collections, yaml
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT, SOURCES, juan_list, load_books
from refs import parse
from bodyline import parse_line

BOOKS = load_books()
OUT = ROOT / "原文"


def citations():
    """{(书简体名, 卷, 段): [(人物文件, id, 姓名)]}"""
    idx = collections.defaultdict(list)
    for f in sorted([*(ROOT / "人物").rglob("*.md"), *(ROOT / "家族").rglob("*.md")]):
        if f.name.startswith("_"):
            continue
        _, head, body = f.read_text(encoding="utf-8").split("---\n", 2)
        meta = yaml.safe_load(head)
        for line in body.splitlines():
            r = parse_line(line)
            if r:
                loc = r[0]
                info, juan, pn, _ = parse(loc)
                lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
                for k in range(lo, hi + 1):
                    who = (f, meta.get("id", ""), meta.get("姓名") or f"{meta.get('家族')}（家族）")
                    if who not in idx[(info["name"], juan, k)]:
                        idx[(info["name"], juan, k)].append(who)
    return idx


def src_note(c):
    if not c:
        return "见 原文/README.md"
    if c[1] == "TLS":
        return "TLS 中华书局点校本"
    return f"[维基文库]({c[2]})（{c[3]}），补 TLS 缺卷" if c[1] == "维基文库" else c[1]


def juan_file(juan: str) -> str:
    m = re.match(r"(\d+)(.*)", juan)
    return f"{int(m[1]):03d}{m[2]}.md"


def main(books):
    cites = citations()
    if not books:
        books = sorted({k[0] for k in cites})
    for name in books:
        info = BOOKS[name]
        d = OUT / info["name"]
        d.mkdir(parents=True, exist_ok=True)
        prov = {}
        pv = SOURCES / name / "来源.tsv"
        for ln in pv.read_text(encoding="utf-8").splitlines() if pv.exists() else []:
            c = ln.split("\t")
            prov[c[0]] = c
        for juan, title, paras in juan_list(name):
            pages = {}
            pf = SOURCES / name / juan_file(juan).replace(".md", ".pages.tsv")
            if pf.exists():
                for ln in pf.read_text(encoding="utf-8").splitlines():
                    k, _, v = ln.partition("\t")
                    pages[int(k)] = v
            lines = [f"# {info['name']}·卷{juan}　{title}", "",
                     f"底本：{src_note(prov.get(juan_file(juan)[:-3]))}。段号即定位符中的“段”。授权与改动说明见 [原文/README.md](../README.md)。", ""]
            for k, p in enumerate(paras, 1):
                pg = f"　<sub>中华本页 {pages[k]}</sub>" if pages.get(k) else ""
                lines.append(f'<a id="p{k}"></a>**〔{k}〕**{pg}　{p}')
                who = cites.get((name, juan, k))
                if who:
                    links = "、".join(f"[{n}](../../{f.relative_to(ROOT).as_posix()})" for f, i, n in who)
                    lines.append(f"\n> 引用此段：{links}")
                lines.append("")
            (d / juan_file(juan)).write_text("\n".join(lines), encoding="utf-8")
        print(f"原文/{info['name']}：{len(juan_list(name))} 卷")


if __name__ == "__main__":
    main(sys.argv[1:])
