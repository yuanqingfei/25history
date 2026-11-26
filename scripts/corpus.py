"""底本读取。底本存放为 sources/<书名>/NNN.md，每卷一个文件，首行“# 篇名”。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"


_NUM = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9}


def cn2int(s: str) -> int:
    total, cur = 0, 0
    for ch in s:
        if ch in _NUM:
            cur = _NUM[ch]
        elif ch == "十":
            total += (cur or 1) * 10; cur = 0
        elif ch == "百":
            total += (cur or 1) * 100; cur = 0
    return total + cur


def juan_key(stem: str) -> str:
    """文件名 007 / 001上 → 卷标记 7 / 1上"""
    return str(int(stem[:3])) + stem[3:]


def juan_file(book: str, juan: str) -> Path:
    m = re.match(r"(\d+)(.*)", str(juan))
    return SOURCES / book / f"{int(m[1]):03d}{m[2]}.md"


def _read(f: Path):
    lines = f.read_text(encoding="utf-8").splitlines()
    title = lines[0].lstrip("# ").strip()
    # 段落 = 去掉标题后的非空行；去掉 markdown 引用符（史记论赞以 "> " 开头）
    paras = [re.sub(r"^>\s*", "", l).strip() for l in lines[1:] if l.strip()]
    return title, paras


def juan_list(book: str):
    """返回 [(卷标记str, 篇名, [段落...])]，段落从 1 起编号（列表下标 +1）。"""
    return [(juan_key(f.stem), *_read(f)) for f in sorted((SOURCES / book).glob("[0-9]*.md"))]


def juan_paras(book: str, juan: str):
    return _read(juan_file(book, juan))[1]


def norm(s: str) -> str:
    """校验用的规范化：只去掉空白，标点和字形都必须一致。"""
    return re.sub(r"\s+", "", s)


def load_books():
    """书目表：返回 {书名或繁体书名: {code, name, fan, juan}}。"""
    books = {}
    for line in (ROOT / "scripts" / "books.tsv").read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        code, name, fan, juan = line.split("\t")
        info = {"code": code, "name": name, "fan": fan, "juan": int(juan)}
        books[name] = books[fan] = info
    return books
