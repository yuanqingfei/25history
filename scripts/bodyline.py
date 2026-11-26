"""传记/家族正文中“引文行”的两种写法，以及二者之间的转换。

1. 独用引文（没有其他文件引用到这些文字）：直接写原文，读者不必跳转。
       > 原文全文〔[史記·7·5](../../原文/史記/007.md#p5)〕
2. 共享引文（与其他文件的引文有重叠）：只写定位符，原文只在底本保存一份。
       > [史記·7·5｜起始…結尾](../../原文/史記/007.md#p5)

两种写法都可以还原成同一个定位符，校验、展开、迁移都按定位符处理。
写法由 scripts/reanchor.py 根据全部文件的引用情况自动决定，不用手工维护。
"""
import os, re, collections
from pathlib import Path
from corpus import ROOT
from refs import resolve, make, _paras, parse

LOC_LINK = re.compile(r"^>\s*\[(?P<loc>[^\]]+｜.+)\]\((?P<url>[^)]+)\)\s*$")
INLINE = re.compile(r"^>\s*(?P<text>.+)〔\[(?P<ref>[^\]｜]+)\]\((?P<url>[^)]+)\)〕\s*$")


def parse_line(line):
    """引文行 → (定位符, 链接url或None, 写法 'shared'/'inline'/'plain')；不是引文行返回 None。"""
    s = line.strip()
    if not s.startswith(">"):
        return None
    m = INLINE.match(s)
    if m:
        return f"{m['ref']}｜{m['text']}", m["url"], "inline"
    m = LOC_LINK.match(s)
    if m:
        return m["loc"], m["url"], "shared"
    return s[1:].strip(), None, "plain"


def para_keys(loc):
    info, juan, pn, _ = parse(loc)
    lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
    return [(info["name"], juan, k) for k in range(lo, hi + 1)]


def url_for(path: Path, meta, lo):
    m = re.match(r"(\d+)(.*)", meta["juan"])
    target = ROOT / "原文" / meta["book"] / f"{int(m[1]):03d}{m[2]}.md"
    return os.path.relpath(target, path.resolve().parent).replace(os.sep, "/") + f"#p{lo}"


def all_files():
    out = []
    for d in ("人物", "家族"):
        out += [p for p in sorted((ROOT / d).rglob("*.md")) if not p.name.startswith(("_", "README"))]
    return out


def span(loc):
    """定位符 → (书, 卷, 起段) 与在拼接段落中的 [起, 止) 字符范围。"""
    text, meta = resolve(loc)
    pn = meta["para"]
    lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
    paras = _paras(meta["name"], meta["juan"])
    offset = sum(len(p) for p in paras[:lo - 1])          # 以整卷为坐标，跨段也能比较
    joined = "".join(paras[lo - 1:hi])
    _, _, _, body = parse(loc)
    i = joined.find(body.split("…")[0]) if "…" in body else joined.find(text)
    return (meta["name"], meta["juan"]), (offset + i, offset + i + len(text))


def citation_map(files=None):
    """{(书, 卷): [(文件, 起, 止)]}：全部文件中每条引文在整卷中的字符范围。"""
    cm = collections.defaultdict(list)
    for f in files or all_files():
        body = f.read_text(encoding="utf-8").split("---\n", 2)[2]
        for line in body.splitlines():
            r = parse_line(line)
            if r:
                key, (a, b) = span(r[0])
                cm[key].append((f.resolve(), a, b))
    return cm


def is_shared(loc, cm, path=None):
    """这条引文是否与其他文件的引文有重叠（重叠即共享）。"""
    key, (a, b) = span(loc)
    me = path.resolve() if path else None
    return any(f != me and x < b and a < y for f, x, y in cm.get(key, ()))


def format_line(path: Path, loc, cm):
    """按共享与否生成规范的引文行。"""
    text, meta = resolve(loc)
    pn = meta["para"]
    lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
    para = "".join(_paras(meta["name"], meta["juan"])[lo - 1:hi])
    url = url_for(path, meta, lo)
    ps = f"{lo}-{hi}" if hi > lo else f"{lo}"
    if is_shared(loc, cm, path):
        return f"> [{make(meta['book'], meta['juan'], pn, para, text)}]({url})"
    return f"> {text}〔[{meta['book']}·{meta['juan']}·{ps}]({url})〕"
