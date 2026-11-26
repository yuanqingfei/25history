"""把 TLS（tls-kr/tls-texts，中华书局点校本，CC BY-SA 4.0）的 TEI XML 转成
sources/<书名>/NNN[上中下].md：每卷一个文件，首行“# 篇名”，之后每段一行。

处理规则：
- 正文：<seg> 中的文字；<c n="X"/> 为标点，照录（“．”改为“。”，“､”改为“、”）。
- 注文 <note> 及注号 <c type="note-ref"> 一律去掉（颜师古注、裴松之注等另行处理）。
- 异文 <app>：取 <lem>（底本采用的读法）。
- 无 Unicode 编码的字 <g n="GJ-xxxx"/>：写作 {GJ-xxxx}。
- 点校本校勘符号（删字用圆括号、补字用方括号）原样保留。
- 每段起始的中华书局本页码写入 NNN.pages.tsv（段号 → 页码）。

用法: python3 scripts/import_tls.py <KR2a00xx.xml> <书名>
"""
import re, sys
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import SOURCES, cn2int

NS = "{http://www.tei-c.org/ns/1.0}"
PUNCT = {"．": "。", "､": "、"}
JUAN = re.compile(r"卷([〇零一二三四五六七八九十百]+)((?:[上中下])?(?:之[上中下])?)")


def text_of(el, page):
    """递归取元素文字；page 为 [当前页码] 的可变容器。"""
    out = [el.text or ""]
    for ch in el:
        tag = ch.tag.replace(NS, "")
        if tag == "note":
            pass
        elif tag == "c":
            if ch.get("type") != "note-ref":
                n = ch.get("n", "")
                out.append(PUNCT.get(n, n))
        elif tag == "g":
            out.append("{" + ch.get("n", "?") + "}")
        elif tag == "pb":
            if page is not None and not page[1]:
                page[1] = ch.get("n")
            if page is not None:
                page[0] = ch.get("n")
        elif tag == "app":
            lem = ch.find(NS + "lem")
            if lem is not None:
                out.append(text_of(lem, page))
        elif tag in ("lb",):
            pass
        else:
            out.append(text_of(ch, page))
        out.append(ch.tail or "")
    return "".join(out)


def apply_jiaokan(book, out):
    """按 scripts/jiaokan.tsv 修补底本。"""
    name = book.split("/")[-1]
    for ln in (Path(__file__).parent / "jiaokan.tsv").read_text(encoding="utf-8").splitlines():
        if not ln or ln.startswith("#"):
            continue
        b, juan, pn, op, old, new, why = ln.split("\t")
        if b != name:
            continue
        m = re.match(r"(\d+)(.*)", juan)
        f = out / f"{int(m[1]):03d}{m[2]}.md"
        lines = f.read_text(encoding="utf-8").split("\n")
        body = [i for i, l in enumerate(lines[1:], 1) if l.strip()]
        i = body[int(pn) - 1]
        if op == "段首补入":
            lines[i] = new + lines[i]
        elif op == "替换":
            assert old in lines[i], (b, juan, pn, old)
            lines[i] = lines[i].replace(old, new, 1)
        f.write_text("\n".join(lines), encoding="utf-8")
        print(f"  校勘 {b} 卷{juan} 第{pn}段：{op}")


def main(xml, book):
    root = ET.parse(xml).getroot()
    out = SOURCES / book
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    page = [None, None]
    n_files, labels = 0, []
    for div in root.iter(NS + "div"):
        head = div.find(NS + "head")
        htxt = re.sub(r"\s+", "", text_of(head, page)) if head is not None else ""
        paras, pages = [], []
        for p in div.findall(NS + "p"):
            page[1] = None
            start = page[0]
            t = re.sub(r"\s+", "", text_of(p, page))
            for a, b in PUNCT.items():
                t = t.replace(a, b)
            t = re.sub(r"【索隱述贊】.*$", "", t)  # 史记卷末司马贞述赞，非正文
            if t:
                paras.append(t)
                pages.append(start or page[1] or "")
        m = JUAN.search(htxt) or (JUAN.search(paras[0]) if paras and len(paras[0]) < 20 else None)
        label = (f"{cn2int(m[1]):03d}{m[2]}" if m else f"x{div.get('n')}")
        title = paras[0] if paras and len(paras[0]) < 30 else htxt
        f = out / f"{label}.md"
        if f.exists():  # 同一卷号出现两次（附录等），追加
            label += "附"; f = out / f"{label}.md"
        f.write_text(f"# {title}\n\n" + "\n\n".join(paras) + "\n", encoding="utf-8")
        (out / f"{label}.pages.tsv").write_text(
            "".join(f"{i}\t{pg}\n" for i, pg in enumerate(pages, 1)), encoding="utf-8")
        n_files += 1; labels.append(label)
    (out / "来源.tsv").write_text("".join(f"{l}\tTLS\thttps://github.com/tls-kr/tls-texts\t{Path(xml).name}\n" for l in labels), encoding="utf-8")
    apply_jiaokan(book, out)
    nums = sorted({int(l[:3]) for l in labels if l[0].isdigit()})
    missing = [i for i in range(1, nums[-1] + 1) if i not in nums] if nums else []
    print(f"{book}\t卷文件 {n_files}\t最大卷号 {nums[-1] if nums else '-'}\t缺卷 {missing[:15]}{'…' if len(missing) > 15 else ''}\t无卷号 {[l for l in labels if l.startswith('x')][:5]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
