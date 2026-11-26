"""规范化文件中的全部定位符：
- 按当前规则重新生成最短锚点（展开后的原文不变）；
- 正文中的定位符写成指向 原文/ 对应段落的链接：> [書·卷·段｜起…止](../../原文/書/NNN.md#pN)
- YAML 中的定位符保持纯文本。
用法: python3 scripts/reanchor.py 文件...
"""
import os, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT
from refs import resolve, make, _paras, REF

LINK = re.compile(r"^\[(?P<loc>.+)\]\((?P<url>[^)]+)\)$")


def norm_loc(loc):
    t, meta = resolve(loc)
    pn = meta["para"]
    lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
    return make(meta["book"], meta["juan"], pn, "".join(_paras(meta["name"], meta["juan"])[lo - 1:hi]), t), meta, lo


def url_for(path: Path, meta, lo):
    m = re.match(r"(\d+)(.*)", meta["juan"])
    target = ROOT / "原文" / meta["book"] / f"{int(m[1]):03d}{m[2]}.md"
    return os.path.relpath(target, path.parent).replace(os.sep, "/") + f"#p{lo}"


def link_line(path, s):
    """'> loc' 或 '> [loc](url)' → 规范化的链接形式"""
    inner = s[1:].strip()
    m = LINK.match(inner)
    loc = m["loc"] if m else inner
    new, meta, lo = norm_loc(loc)
    return f"> [{new}]({url_for(path, meta, lo)})"


def process(path: Path):
    raw = path.read_text(encoding="utf-8")
    _, head, body = raw.split("---\n", 2)
    hl = []
    for line in head.split("\n"):
        m = re.match(r"^(\s*-\s+|\s*[^:\s][^:]*:\s+)(.+)$", line)
        if m and REF.match(m[2].strip()):
            line = m[1] + norm_loc(m[2].strip())[0]
        hl.append(line)
    bl = [link_line(path, l.strip()) if l.strip().startswith(">") else l for l in body.split("\n")]
    path.write_text("---\n" + "\n".join(hl) + "---\n" + "\n".join(bl), encoding="utf-8")


if __name__ == "__main__":
    for f in sys.argv[1:]:
        process(Path(f).resolve())
