"""定位符：传记中引用原文的唯一方式。原文本身只存在于底本（sources/），不在传记里重复保存。

格式:  書名·卷·段｜起…止      或    書名·卷·段｜全文
例:    史記·7·9｜陳嬰者，故東陽…稱為長者。
       漢書·31·1｜范增

- 書名：books.tsv 中的书名（写简体；繁体书名也能识别，以兼容旧文件）
- 卷：卷标记，如 7、1上、27中之下
- 段：该卷的第几段（非空行，从 1 起）。底本分段有误、一句话被断在两段时，可写 31-32（最多跨 3 段，按无缝连接展开）
- 起…止：起始几字与结束几字，中间用一个“…”分隔，展开为两者之间（含）的原文。
  起始字串在该段中必须唯一；结束字串取起始之后的第一次出现。
- 没有“…”时，竖线后的文字就是全文，必须在该段中出现。
"""
import re
from functools import lru_cache
from corpus import load_books, juan_paras

REF = re.compile(r"^(?P<book>[^·｜\s]+)·(?P<juan>\d+[^·｜]*)·(?P<para>\d+(?:-\d+)?)｜(?P<body>.+)$")
SEP = "…"
BOOKS = load_books()


class RefError(Exception):
    pass


@lru_cache(maxsize=None)
def _paras(book, juan):
    return juan_paras(book, juan)


def parse(s: str):
    m = REF.match(s.strip())
    if not m:
        raise RefError(f"定位符格式错误: {s[:30]}")
    info = BOOKS.get(m["book"])
    if not info:
        raise RefError(f"未知书名: {m['book']}")
    a, _, b = m["para"].partition("-")
    pn = (int(a), int(b)) if b else int(a)
    return info, m["juan"], pn, m["body"]


def resolve(s: str):
    """返回 (原文, 元信息dict)。出错抛 RefError。"""
    info, juan, pn, body = parse(s)
    try:
        paras = _paras(info.get("dir", info["name"]), juan)
    except FileNotFoundError:
        raise RefError(f"找不到底本 {info['name']} 卷{juan}（先运行 scripts/fetch_sources.sh）")
    lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
    if not (1 <= lo <= hi <= len(paras)) or (isinstance(pn, tuple) and hi - lo > 2):
        raise RefError(f"{info['name']}卷{juan} 段号 {pn} 不存在（跨段最多 3 段）")
    p = "".join(paras[lo - 1:hi])
    if body.count(SEP) > 1:
        raise RefError(f"一个定位符只能有一个“{SEP}”: {body[:30]}")
    if SEP in body:
        a, b = body.split(SEP)
        if p.count(a) != 1:
            raise RefError(f"起始字串在段中{'不存在' if a not in p else '不唯一'}: {a}")
        i = p.find(a)
        j = p.find(b, i + len(a))
        if j < 0:
            raise RefError(f"起始字串之后找不到结束字串: {b}")
        text = p[i:j + len(b)]
    else:
        if body not in p:
            raise RefError(f"原文不在该段中: {body[:30]}")
        text = body
    meta = {"book": info["name"], "name": info.get("dir", info["name"]), "juan": juan, "para": pn}
    return text, meta


def make(book: str, juan: str, pn, para: str, text: str, full_max=40, min_len=8):
    """为段 para 中的一段原文 text 生成最短的定位符。pn 可为 int 或 (起, 止)。"""
    ps = f"{pn[0]}-{pn[1]}" if isinstance(pn, tuple) else pn
    head = f"{book}·{juan}·{ps}｜"
    if len(text) <= full_max:
        return head + text
    i0 = para.find(text)
    assert i0 >= 0
    for la in range(min_len, len(text)):
        a = text[:la]
        if para.count(a) == 1:
            break
    for lb in range(min_len, len(text)):
        b = text[-lb:]
        if para.find(b, i0 + la) == i0 + len(text) - lb:
            break
    if la + lb >= len(text):
        return head + text
    return head + a + SEP + b
