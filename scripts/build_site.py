"""生成静态网站到 _site/（GitHub Pages 发布；搜索索引由 Pagefind 另行生成）。

页面与网址（人物网址只用永久编号，永不改变）：
  index.html                首页：搜索、统计、浏览入口
  p/<编号>.html             人物传
  f/<家族>.html             家族（世系图）
  y/<书>/<卷>.html          原文（每段带锚点 #pN，列出引用此段的人物）
  list/*.html               人物总表、按品评、按身份、按书
  about.html                说明

用法: python3 scripts/build_site.py   （需要 sources/ 中有被引用到的书，见 scripts/needed_books.py）
"""
import html, json, re, shutil, sys, collections
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT, SOURCES, juan_list, load_books
from refs import resolve
from bodyline import parse_line
from reanchor import split_section, HX_ITEM, item_loc
from infobox import BLOCK, roster
import opencc

OUT = ROOT / "_site"
BOOKS = load_books()
ORDER = [l.split("\t")[0] for l in (ROOT / "scripts" / "dibens.tsv").read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
S2T = opencc.OpenCC("s2t")
E = html.escape
SITE = "二十五史人物传"


# ───────────── 读取数据 ─────────────
def read_doc(p: Path):
    _, head, body = p.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(head), BLOCK.sub("", body)


def loc_info(loc):
    """定位符 → dict(text, book, juan, lo, hi)"""
    text, m = resolve(loc)
    pn = m["para"]
    lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
    return {"text": text, "book": m["name"], "juan": m["juan"], "lo": lo, "hi": hi}


def parse_body(body):
    """→ {"main": [引文], "后世": [...], "品评依据": [...], "互见": [...]}"""
    out = collections.defaultdict(list)
    sec = "main"
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("## "):
            sec = s[3:].strip(); continue
        if s.startswith("#") or not s:
            continue
        r = parse_line(s)
        if r:
            out[sec].append(loc_info(r[0])); continue
        m = HX_ITEM.match(s)
        if m:
            out[sec].append(loc_info(item_loc(m)))
    return out


def juan_file(juan):
    m = re.match(r"(\d+)(.*)", juan)
    return f"{int(m[1]):03d}{m[2]}"


def yurl(q, depth):
    """原文链接"""
    return f"{'../' * depth}y/{q['book']}/{juan_file(q['juan'])}.html#p{q['lo']}"


def cite_label(q):
    ps = f"{q['lo']}-{q['hi']}" if q["hi"] > q["lo"] else f"{q['lo']}"
    return f"{q['book']}·{q['juan']}·{ps}"


def juan_title(book, juan, _c={}):
    if book not in _c:
        _c[book] = {j: t for j, t, _ in juan_list(book)}
    return _c[book].get(juan, "")


# ───────────── 页面框架 ─────────────
CSS = """
:root{--ink:#222;--muted:#777;--line:#e5e0d6;--bg:#fbf8f2;--accent:#8b2c1a;--card:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.85 "Noto Serif SC","Source Han Serif SC","Songti SC",serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header.top{border-bottom:1px solid var(--line);background:#fff}
header.top .in{max-width:960px;margin:auto;padding:10px 20px;display:flex;gap:20px;align-items:center;flex-wrap:wrap}
header.top .brand{font-weight:700;font-size:20px;color:var(--ink)}header.top nav a{margin-right:14px;font-size:15px}
main{max-width:960px;margin:auto;padding:24px 20px 60px}
h1{font-size:32px;margin:.2em 0}h2{font-size:21px;margin:1.8em 0 .6em;padding-bottom:4px;border-bottom:1px solid var(--line)}
.sub{color:var(--muted);font-size:15px}
table.info{border-collapse:collapse;margin:12px 0 18px;background:var(--card);font-size:15px}
table.info th,table.info td{border:1px solid var(--line);padding:6px 12px;text-align:left;vertical-align:top}
table.info th{background:#f3eee4;font-weight:600;white-space:nowrap}
blockquote{margin:0 0 14px;padding:10px 16px;background:var(--card);border-left:3px solid var(--accent)}
.src{font-size:13px;color:var(--muted);white-space:nowrap}.src a{color:var(--muted)}
ul.plain{padding-left:1.2em}ul.plain li{margin:4px 0}
details{margin:6px 0;font-size:14px;color:#555}summary{cursor:pointer}
.note{font-size:14px;color:#555;background:#f3eee4;padding:8px 12px;border-radius:4px;margin:6px 0}
.tag{display:inline-block;padding:0 8px;border-radius:10px;font-size:13px;background:#efe6d8;margin-right:4px}
.tag.君子{background:#dfeedd}.tag.小人{background:#f6e2c9}.tag.恶贼{background:#f3d0cb}
.para{margin:0 0 14px;padding:8px 12px;background:var(--card);border:1px solid transparent}
.para:target{border-color:var(--accent);background:#fff8e8}
.pn{font-size:13px;color:var(--muted);margin-right:6px}.pg{font-size:12px;color:#aaa;margin-right:6px}
.cites{font-size:14px;margin-top:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);padding:10px 14px;border-radius:6px}
.big{font-size:28px;font-weight:700;color:var(--accent)}
table.list{border-collapse:collapse;width:100%;font-size:15px;background:var(--card)}
table.list td,table.list th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left}
#search{margin:18px 0 26px}
.mermaid{background:#fff;padding:12px;border:1px solid var(--line)}
footer{color:var(--muted);font-size:13px;text-align:center;padding:30px}
"""


def page(title, body, depth=0, search=True, extra_head="", index=True):
    r = "../" * depth
    nav = (f'<a href="{r}index.html">搜索</a><a href="{r}list/all.html">人物总表</a>'
           f'<a href="{r}list/pingping.html">按品评</a><a href="{r}list/shenfen.html">按身份</a>'
           f'<a href="{r}list/families.html">家族</a><a href="{r}about.html">说明</a>')
    body_attr = "" if index else " data-pagefind-ignore=\"all\""
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · {SITE}</title><link rel="stylesheet" href="{r}style.css">{extra_head}</head>
<body{body_attr}><header class="top"><div class="in"><a class="brand" href="{r}index.html">{SITE}</a><nav>{nav}</nav></div></header>
<main>{body}</main>
<footer>正文皆为史书原文。底本：TLS 中华书局点校本、维基文库（CC BY-SA 4.0）·
<a href="https://github.com/yuanqingfei/25history">GitHub 仓库</a></footer></body></html>"""


def quote_html(q, depth):
    return (f'<blockquote>{E(q["text"])} <span class="src">〔<a href="{yurl(q, depth)}">'
            f'{E(cite_label(q))} {E(juan_title(q["book"], q["juan"]))}</a>〕</span></blockquote>')


def date_cell(d):
    if not d:
        return ""
    s = E(d.get("公元") or "")
    extra = []
    if d.get("原文纪年"):
        extra.append(f"原文纪年：{E(d['原文纪年'])}")
    if d.get("推算"):
        extra.append(E(d["推算"]))
    if extra:
        s += f'<details><summary>推算</summary>{"<br>".join(extra)}</details>'
    return s


# ───────────── 人物页 ─────────────
def build_people(people, fam_of, depth=1):
    for pid, (path, meta, parts) in people.items():
        sz = meta.get("生卒") or {}
        fams = "、".join(f'<a href="../f/{E(fn)}.html">{E(fn)}</a>' for fn in fam_of.get(pid, [])) or "—"
        alias = meta.get("别称") or []
        first = path.parent.name
        rows = [("编号", E(pid)), ("别称", E("、".join(alias)) or "—"), ("时代", E(meta.get("时代", ""))),
                ("籍贯", E(meta.get("籍贯", "") or "")), ("生", date_cell(sz.get("生"))), ("卒", date_cell(sz.get("卒"))),
                ("身份", E(meta.get("身份", ""))),
                ("品评", f'<span class="tag {E(meta.get("品评", ""))}">{E(meta.get("品评", ""))}</span>'
                        f'<span class="sub">依据：{E(meta.get("品评依据类型", ""))}</span>'),
                ("家族", fams), ("首见", E(first))]
        if meta.get("类传"):
            rows.insert(8, ("类传", E(meta["类传"])))
        info = "<table class=info>" + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</table>"
        b = [f'<h1 data-pagefind-meta="title">{E(meta["姓名"])}</h1>',
             f'<p hidden data-pagefind-weight="10">{E(" ".join([meta["姓名"], *alias]))} '
             f'{E(S2T.convert(" ".join([meta["姓名"], *alias])))}</p>',
             f'<span hidden data-pagefind-filter="品评">{E(meta.get("品评", ""))}</span>'
             f'<span hidden data-pagefind-filter="身份">{E(meta.get("身份", ""))}</span>'
             f'<span hidden data-pagefind-filter="首见">{E(first)}</span>'
             f'<span hidden data-pagefind-filter="类型">人物</span>',
             info, "<h2>传</h2>"] + [quote_html(q, depth) for q in parts.get("main", [])]
        if parts.get("后世"):
            b += ["<h2>后世</h2>"] + [quote_html(q, depth) for q in parts["后世"]]
        if parts.get("品评依据"):
            b += ["<h2>品评依据</h2>"] + [quote_html(q, depth) for q in parts["品评依据"]]
        if meta.get("推断理由"):
            b.append(f'<div class="note">推断理由：{E(meta["推断理由"])}</div>')
        if parts.get("互见"):
            b += ["<h2>互见</h2><ul class=plain data-pagefind-ignore>"] + [
                f'<li>{E(q["text"])} <span class="src">〔<a href="{yurl(q, depth)}">{E(cite_label(q))}</a>〕</span></li>'
                for q in parts["互见"]] + ["</ul>"]
        notes = [(k, meta.get(k)) for k in ("备注", "异文", "消歧", "待补") if meta.get(k)]
        scan = meta.get("全史扫描")
        if notes or scan:
            b.append("<h2>附记</h2><div data-pagefind-ignore>")
            b += [f'<div class="note">{k}：{E(str(v))}</div>' for k, v in notes]
            if scan:
                b.append(f'<div class="note">全史扫描：{E(scan.get("范围", ""))}，命中 {scan.get("命中", "")}，'
                         f'收入后世 {scan.get("收入后世", "")}，列入互见 {scan.get("列入互见", "")}。排除：{E(str(scan.get("排除", "")))}</div>')
            b.append(f'<div class="note">已查：{E("、".join(meta.get("已查") or []))}。校对状态：{E(meta.get("校对状态", ""))}</div></div>')
        b.append(f'<p class="sub" data-pagefind-ignore>源文件：<a href="https://github.com/yuanqingfei/25history/blob/main/{E(path.relative_to(ROOT).as_posix())}">'
                 f'{E(path.relative_to(ROOT).as_posix())}</a></p>')
        body = "<article data-pagefind-body>" + "\n".join(b) + "</article>"
        (OUT / "p" / f"{pid}.html").write_text(page(meta["姓名"] + "传", body, depth), encoding="utf-8")


# ───────────── 家族页 ─────────────
def build_families(fams, people, names):
    MERMAID = '<script type="module">import m from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";m.initialize({startOnLoad:true});</script>'
    from infobox import family_block
    for fp, meta, parts in fams:
        name = fp.stem
        mem = meta.get("成员") or []
        blk = family_block(fp, meta)
        mer = re.search(r"```mermaid\n(.*?)```", blk, re.S)[1]
        rows = []
        for m in sorted(mem, key=lambda m: (not str(m.get("世代", "")).isdigit(), str(m.get("世代", "")).zfill(3))):
            link = f'<a href="../p/{E(m["id"])}.html">{E(m["姓名"])}</a>' if m["id"] in people else f'{E(m["姓名"])}<span class="sub">（未立传）</span>'
            rows.append(f'<tr><td>{E(str(m.get("世代", "")))}</td><td>{link}</td><td>{E(m.get("关系", ""))}</td></tr>')
        b = [f'<article data-pagefind-body><h1>{E(name)}</h1><span hidden data-pagefind-filter="类型">家族</span>',
             f'<p class="sub">{E(meta.get("时代", ""))}</p><h2>世系图</h2><pre class="mermaid">{E(mer)}</pre>',
             "<h2>成员</h2><table class=list><tr><th>世代</th><th>成员</th><th>关系</th></tr>" + "".join(rows) + "</table>"]
        if parts.get("main"):
            b += ["<h2>家族记载</h2>"] + [quote_html(q, 1) for q in parts["main"]]
        if meta.get("待补"):
            b.append(f'<div class="note">待补：{E(meta["待补"])}</div>')
        b.append("</article>")
        (OUT / "f" / f"{name}.html").write_text(page(name, "\n".join(b), 1, extra_head=MERMAID), encoding="utf-8")


# ───────────── 原文页 ─────────────
def build_yuanwen(people, fams):
    cites = collections.defaultdict(list)          # (书, 卷, 段) → [(编号, 姓名)]
    for pid, (_, meta, parts) in people.items():
        for q in parts.get("main", []) + parts.get("后世", []):
            for k in range(q["lo"], q["hi"] + 1):
                if (pid, meta["姓名"]) not in cites[(q["book"], q["juan"], k)]:
                    cites[(q["book"], q["juan"], k)].append((pid, meta["姓名"]))
    wanted = {(p.parent.name, p.stem) for p in (ROOT / "原文").rglob("[0-9]*.md")}
    n = 0
    for book, jstem in sorted(wanted):
        juan = str(int(jstem[:3])) + jstem[3:]
        paras = next((ps for j, t, ps in juan_list(book) if j == juan), None)
        if paras is None:
            continue
        pages = {}
        pf = SOURCES / book / f"{jstem}.pages.tsv"
        if pf.exists():
            for ln in pf.read_text(encoding="utf-8").splitlines():
                k, _, v = ln.partition("\t"); pages[int(k)] = v
        title = juan_title(book, juan)
        b = [f'<article data-pagefind-body><h1>{E(book)}·卷{E(juan)}</h1><p class="sub">{E(title)}</p>',
             f'<span hidden data-pagefind-filter="类型">原文</span><span hidden data-pagefind-meta="title">{E(book)}·卷{E(juan)} {E(title)}</span>']
        for k, p in enumerate(paras, 1):
            who = cites.get((book, juan, k))
            c = ('<div class="cites" data-pagefind-ignore>涉及：' + "、".join(f'<a href="../../p/{E(i)}.html">{E(nm)}</a>' for i, nm in who) + "</div>") if who else ""
            pg = f'<span class="pg">中华本页 {E(pages[k])}</span>' if pages.get(k) else ""
            b.append(f'<div class="para" id="p{k}"><span class="pn">〔{k}〕</span>{pg}{E(p)}{c}</div>')
        b.append("</article>")
        d = OUT / "y" / book
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{jstem}.html").write_text(page(f"{book}·卷{juan}", "\n".join(b), 2), encoding="utf-8")
        n += 1
    return n


# ───────────── 列表页与首页 ─────────────
def build_lists(people, fams, names):
    built = set(people)
    # 人物总表：各卷人物表
    rows = []
    for t in sorted((ROOT / "人物").rglob("_*人物表.tsv")):
        lines = t.read_text(encoding="utf-8").splitlines()
        rows.append(f'<tr><th colspan=4>{E(t.parent.name)}·{E(t.stem.lstrip("_"))}</th></tr>')
        for ln in lines[1:]:
            c = ln.split("\t") + [""] * 6
            nm = f'<a href="../p/{E(c[0])}.html">{E(c[1])}</a>' if c[0] in built else E(c[1])
            rows.append(f"<tr><td>{E(c[0])}</td><td>{nm}</td><td>{E(c[2])}</td><td>{E(c[3])}</td></tr>")
    body = (f"<h1>人物总表</h1><p class=sub>已立传 {len(built)} 人；名单中带链接者为已立传。</p>"
            "<table class=list><tr><th>编号</th><th>姓名</th><th>称谓</th><th>备注</th></tr>" + "".join(rows) + "</table>")
    (OUT / "list" / "all.html").write_text(page("人物总表", body, 1, index=False), encoding="utf-8")

    def grouped(field, order, fname, title):
        g = collections.defaultdict(list)
        for pid, (_, meta, _) in people.items():
            g[meta.get(field, "")].append((pid, meta))
        keys = [k for k in order if k in g] + sorted(k for k in g if k not in order)
        b = [f"<h1>{title}</h1>"]
        for k in keys:
            b.append(f"<h2>{E(k)}（{len(g[k])}）</h2><div class=grid>")
            b += [f'<div class=card><a href="../p/{E(pid)}.html">{E(m["姓名"])}</a> <span class=sub>{E(m.get("时代", ""))}</span></div>'
                  for pid, m in sorted(g[k], key=lambda x: x[0])]
            b.append("</div>")
        (OUT / "list" / fname).write_text(page(title, "\n".join(b), 1, index=False), encoding="utf-8")
    grouped("品评", ["君子", "普通", "小人", "恶贼"], "pingping.html", "按品评")
    grouped("身份", ["帝王", "国王", "后妃", "宗室", "臣属", "将领", "士民", "妇女", "四夷", "方外", "其他"], "shenfen.html", "按身份")
    b = ["<h1>家族</h1><div class=grid>"] + [f'<div class=card><a href="../f/{E(fp.stem)}.html">{E(fp.stem)}</a>'
         f'<br><span class=sub>{len(m.get("成员") or [])} 人</span></div>' for fp, m, _ in fams] + ["</div>"]
    (OUT / "list" / "families.html").write_text(page("家族", "\n".join(b), 1, index=False), encoding="utf-8")


def build_index(people, fams, n_yuan, n_roster):
    stats = [(len(people), "已立传"), (n_roster, "人物表已收"), (len(fams), "家族"), (n_yuan, "原文卷")]
    cards = "".join(f'<div class=card><div class=big>{n}</div>{t}</div>' for n, t in stats)
    body = f"""<h1>{SITE}</h1>
<p>为二十五史（二十四史＋《清史稿》）中出现的每一个人立一篇纪传体传记：正文全部是史书原文，逐字校验，每句可点击跳到底本原文。</p>
<div id="search"></div><div class=grid>{cards}</div>
<h2>浏览</h2><p><a href="list/all.html">人物总表</a> · <a href="list/pingping.html">按品评</a> · <a href="list/shenfen.html">按身份</a> · <a href="list/families.html">家族</a></p>
<p class=sub>搜索支持简体、繁体、别称（如“亚父”）与正文词句；可按 类型（人物／原文／家族）、品评、身份 筛选。</p>
<link href="pagefind/pagefind-ui.css" rel="stylesheet"><script src="pagefind/pagefind-ui.js"></script><script src="t2s.js"></script>
<script>window.addEventListener('DOMContentLoaded',()=>{{new PagefindUI({{element:"#search",showSubResults:true,
processTerm:t=>t2s(t),translations:{{placeholder:"输入人名、别称或词句，如：亚父、项伯、鸿门",zero_results:"没有找到“[SEARCH_TERM]”",
many_results:"找到 [COUNT] 条结果",one_result:"找到 1 条结果",filters_label:"筛选",load_more:"更多结果",search_label:"搜索"}}}});}});</script>"""
    (OUT / "index.html").write_text(page(SITE, body, 0, index=False), encoding="utf-8")


def build_about():
    body = f"""<h1>说明</h1>
<h2>原则</h2><ul class=plain><li>传记正文只用二十五史原文，由程序逐字核对底本；AI 只负责找、选、排，不负责写。</li>
<li>品评按修史者当时的价值观：类传归属优先，其次史臣论赞、史家叙评、书中人物评语，最后才是本项目据言行所作推断（必附理由）。</li>
<li>生卒以公元纪年；推算而不确定者加“？”，并说明依据。秦及汉初以十月为岁首。</li>
<li>人物编号永久不变，网址可放心引用。</li></ul>
<h2>底本</h2><p>多数史书用 TLS（Thesaurus Linguae Sericae）据中华书局点校本整理的文本；周书、宋史、明史、清史稿及若干缺卷用维基文库。均为繁体，自动转为简体工作文本。授权 CC BY-SA 4.0。详见仓库
<a href="https://github.com/yuanqingfei/25history/blob/main/docs/底本说明.md">底本说明</a> 与
<a href="https://github.com/yuanqingfei/25history/blob/main/docs/编写规范.md">编写规范</a>。</p>"""
    (OUT / "about.html").write_text(page("说明", body, 0, index=False), encoding="utf-8")


def build_t2s():
    """浏览器端查询词繁转简：单字对照表"""
    c = opencc.OpenCC("t2s")
    import unicodedata
    m = {}
    for cp in range(0x3400, 0x9FFF + 1):
        ch = chr(cp); s = c.convert(ch)
        if s != ch and len(s) == 1:
            m[ch] = s
    js = "var T2S=" + json.dumps("".join(k + v for k, v in m.items()), ensure_ascii=False) + ";" \
         "var T2SM=(function(){var o={};for(var i=0;i<T2S.length;i+=2)o[T2S[i]]=T2S[i+1];return o})();" \
         "function t2s(t){return Array.from(t).map(function(c){return T2SM[c]||c}).join('')}"
    (OUT / "t2s.js").write_text(js, encoding="utf-8")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    for d in ("p", "f", "y", "list"):
        (OUT / d).mkdir(parents=True)
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    people = {}
    for p in sorted((ROOT / "人物").rglob("*.md")):
        if p.name.startswith("_"):
            continue
        meta, body = read_doc(p)
        people[meta["id"]] = (p, meta, parse_body(body))
    fams = []
    for p in sorted((ROOT / "家族").glob("*.md")):
        meta, body = read_doc(p)
        fams.append((p, meta, parse_body(body)))
    fam_of = collections.defaultdict(list)
    for fp, m, _ in fams:
        for x in m.get("成员") or []:
            fam_of[x["id"]].append(fp.stem)
    names = roster()
    build_people(people, fam_of)
    build_families(fams, people, names)
    n_yuan = build_yuanwen(people, fams)
    build_lists(people, fams, names)
    build_index(people, fams, n_yuan, len(names))
    build_about()
    build_t2s()
    print(f"网站：人物 {len(people)} 页，家族 {len(fams)} 页，原文 {n_yuan} 卷 → _site/")


if __name__ == "__main__":
    main()
