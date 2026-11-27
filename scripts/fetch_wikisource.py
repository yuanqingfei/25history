"""从维基文库（zh.wikisource.org）下载史书，供 GitHub Actions 使用（本地沙箱无法访问维基文库）。

对每部书：
1. 用 API list=allpages 列出“書名/”开头的全部子页面，筛出“卷N”页；
2. 逐页 action=parse 取渲染后的 HTML，去掉页眉、导航、编辑链接、注释与参考文献，
   按段落（p、dd、标题、诗、表格行）输出纯文本；
3. 写入 底本/维基文库/<書名>/NNN[上中下].md（首行“# 页面标题”），
   并在 manifest.tsv 记录 页面标题、卷标记、revid、时间戳、URL，便于追溯。

用法: python scripts/fetch_wikisource.py --books 周書,宋史 [--out 底本/维基文库] [--only 舊唐書:191-200]
"""
import argparse, re, sys, time, json
from pathlib import Path
import requests
from bs4 import BeautifulSoup

API = "https://zh.wikisource.org/w/api.php"
UA = "25history-bot/0.1 (https://github.com/yuanqingfei/25history; research, polite)"
S = requests.Session()
S.headers["User-Agent"] = UA

NUM = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def cn2int(s):
    if s.isdigit():
        return int(s)
    total, cur = 0, 0
    for ch in s:
        if ch in NUM:
            cur = NUM[ch]
        elif ch == "十":
            total += (cur or 1) * 10; cur = 0
        elif ch == "百":
            total += (cur or 1) * 100; cur = 0
    return total + cur


JUAN = re.compile(r"卷([0-9〇零一二三四五六七八九十百]+)((?:[上中下])?(?:之[上中下])?)$")


def api(**params):
    params.update(format="json", formatversion=2)
    for attempt in range(5):
        try:
            r = S.get(API, params=params, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(r.status_code)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"  重试 {attempt + 1}（{e}），{wait}s 后", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"API 失败: {params}")


def list_subpages(book):
    titles, cont = [], {}
    while True:
        d = api(action="query", list="allpages", apprefix=f"{book}/", apnamespace=0, aplimit="max", **cont)
        titles += [p["title"] for p in d["query"]["allpages"]]
        if "continue" not in d:
            return titles
        cont = d["continue"]


DROP_SEL = [
    "#headertemplate", ".headertemplate", ".header_container", ".ws-header", ".ws-noexport", ".noprint",
    ".navbox", ".mw-editsection", "sup.reference", ".reference", "ol.references", ".references", ".toc",
    ".licenseContainer", ".mw-references-wrap", "style", "script", ".mw-empty-elt",
]


def html_to_paras(html):
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(".mw-parser-output") or soup
    for sel in DROP_SEL:
        for el in root.select(sel):
            el.decompose()
    # 页眉模板常为页面最前面的 table，含“作者”“姊妹计划”等字样
    for t in root.find_all("table"):
        if re.search(r"姊妹計劃|姊妹计划|作者：|上一卷|下一卷|返回", t.get_text()):
            t.decompose()
    paras = []
    for el in root.find_all(["p", "dd", "h2", "h3", "h4", "div", "tr"]):
        if el.name == "div" and "poem" not in (el.get("class") or []):
            continue
        if el.name != "tr" and el.find_parent("table") is not None:
            continue          # 表格单元格里的段落已随整行输出，不再单独输出
        if el.name == "tr":
            cells = [c.get_text("", strip=True) for c in el.find_all(["td", "th"])]
            t = "｜".join(c for c in cells)
        else:
            t = el.get_text("", strip=True)
        t = re.sub(r"\s+", "", t)
        if t and (not paras or paras[-1] != t):
            paras.append(t)
    return paras


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", required=True)
    ap.add_argument("--out", default="底本/维基文库")
    ap.add_argument("--only", default="", help="書名:起-止[,書名:起-止]，只下载这些卷号")
    ap.add_argument("--sleep", type=float, default=0.5)
    a = ap.parse_args()
    only = {}
    for x in filter(None, a.only.split(",")):
        b, rng = x.split(":"); lo, hi = map(int, rng.split("-")); only[b] = (lo, hi)
    for book in a.books.split(","):
        out = Path(a.out) / book
        out.mkdir(parents=True, exist_ok=True)
        titles = list_subpages(book)
        juans = []
        for t in titles:
            m = JUAN.search(t[len(book) + 1:])
            if m and "/" not in t[len(book) + 1:]:
                juans.append((cn2int(m[1]), m[2], t))
        juans.sort()
        if book in only:
            lo, hi = only[book]; juans = [j for j in juans if lo <= j[0] <= hi]
        print(f"{book}：子页面 {len(titles)} 个，其中卷页 {len(juans)} 个", flush=True)
        if book in only:
            print("  范围内的卷页：", [t for _, _, t in juans], flush=True)
            print("  未识别为卷页的子页面：", [t for t in titles if not JUAN.search(t[len(book) + 1:])][:60], flush=True)
        if not juans:
            print("  未找到卷页，前 20 个子页面：", titles[:20], flush=True)
            continue
        manifest = []
        for n, part, title in juans:
            d = api(action="parse", page=title, prop="text|revid", redirects=1, disableeditsection=1)
            if "error" in d:
                print(f"  ！{title}: {d['error']}", flush=True); continue
            paras = html_to_paras(d["parse"]["text"])
            label = f"{n:03d}{part}"
            (out / f"{label}.md").write_text(f"# {title}\n\n" + "\n\n".join(paras) + "\n", encoding="utf-8")
            manifest.append((title, label, str(d["parse"].get("revid", "")), time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                             "https://zh.wikisource.org/wiki/" + title.replace(" ", "_")))
            print(f"  {label}\t{len(paras)} 段\t{sum(map(len, paras))} 字", flush=True)
            time.sleep(a.sleep)
        mf = out / "manifest.tsv"
        old = {}
        if mf.exists():
            for ln in mf.read_text(encoding="utf-8").splitlines():
                c = ln.split("\t"); old[c[1]] = c
        for row in manifest:
            old[row[1]] = list(row)
        mf.write_text("".join("\t".join(r) + "\n" for _, r in sorted(old.items())), encoding="utf-8")


if __name__ == "__main__":
    main()
