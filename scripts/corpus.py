"""底本读取。底本存放为 sources/<书名>/NNN.md，每卷一个文件，首行“# 篇名”。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources"


def juan_list(book: str):
    """返回 [(卷号int, 篇名, 正文)]。"""
    out = []
    for f in sorted((SOURCES / book).glob("[0-9]*.md")):
        lines = f.read_text(encoding="utf-8").splitlines()
        title = lines[0].lstrip("# ").strip()
        out.append((int(f.stem), title, "\n".join(lines[1:])))
    return out


def juan_text(book: str, n: int) -> str:
    return (SOURCES / book / f"{n:03d}.md").read_text(encoding="utf-8")


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
