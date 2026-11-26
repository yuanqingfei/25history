"""把殆知阁的整书文本切成 sources/<书名>/NNN[上中下].md（每卷一个文件，首行“# 篇名”）。
用法: python3 scripts/import_daizhige.py <殆知阁txt> <书名>
只适配“开头有目录、正文以“卷X”行分卷”的文本；切完会打印卷数，需对照 books.tsv 人工确认。
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import SOURCES, cn2int

HEAD = re.compile(r"^卷([〇零一二三四五六七八九十百]+)((?:[上中下])?(?:之[上中下])?)\s*(.*)$")
src, book = Path(sys.argv[1]), sys.argv[2]
lines = src.read_text(encoding="utf-8").splitlines()
seen, body_start, toc_title = set(), None, {}
for i, ln in enumerate(lines):
    m = HEAD.match(ln.strip())
    if m:
        key = (cn2int(m[1]), m[2])
        if key in seen:
            body_start = i; break
        seen.add(key); toc_title[key] = m[3].strip()
heads = []
for i in range(body_start, len(lines)):
    m = HEAD.match(lines[i].strip())
    if m:
        heads.append((i, (cn2int(m[1]), m[2]), m[3].strip()))
out = SOURCES / book
out.mkdir(parents=True, exist_ok=True)
for f in out.glob("*.md"):
    f.unlink()
for k, (i, key, title) in enumerate(heads):
    e = heads[k + 1][0] if k + 1 < len(heads) else len(lines)
    title = title or toc_title.get(key, "")
    paras = [l.strip() for l in lines[i + 1:e] if l.strip()]
    (out / f"{key[0]:03d}{key[1]}.md").write_text(f"# {title}\n\n" + "\n\n".join(paras) + "\n", encoding="utf-8")
print(book, "切出", len(heads), "个卷文件，最大卷号", max(h[1][0] for h in heads))
