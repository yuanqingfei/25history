"""规范化全部人物与家族文件中的引文：
- 正文：独用段落写原文全文＋出处链接；共享段落写定位符链接（见 scripts/bodyline.py）。
  是否共享按全部文件统计，所以每次都处理全部文件。
- YAML：定位符保持纯文本，按当前规则重算最短锚点。
用法: python3 scripts/reanchor.py
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from refs import resolve, make, _paras, REF
from bodyline import parse_line, format_line, citation_map, all_files
from infobox import info_block, family_block, insert_block, strip_block, families, person_files, roster
import yaml


def short(loc):
    t, meta = resolve(loc)
    pn = meta["para"]
    lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
    return make(meta["book"], meta["juan"], pn, "".join(_paras(meta["name"], meta["juan"])[lo - 1:hi]), t)


def process(path: Path, cm, ctx):
    _, head, body = path.read_text(encoding="utf-8").split("---\n", 2)
    body = strip_block(body)
    hl = []
    for line in head.split("\n"):
        m = re.match(r"^(\s*-\s+|\s*[^:\s][^:]*:\s+)(.+)$", line)
        if m and REF.match(m[2].strip()):
            line = m[1] + short(m[2].strip())
        hl.append(line)
    meta = yaml.safe_load("\n".join(hl))
    # 互见：旧文件在 YAML 里，迁到正文末尾的“## 互见”一节（竖排、可点击）
    hx = [str(x) for x in (meta.pop("互见", None) or [])]
    if hx:
        hl = [l for l in yaml_without(hl, "互见")]
    body, hx_body = split_huxian(body)
    hx = hx_body + [x for x in hx if x not in hx_body]
    bl = []
    for line in body.split("\n"):
        r = parse_line(line)
        bl.append(format_line(path, r[0], cm) if r else line)
    body = "\n".join(bl).rstrip("\n") + "\n"
    if hx:
        body += "\n## 互见\n\n" + "\n".join(huxian_line(path, x) for x in hx) + "\n"
    if "人物" in path.parts:
        body = insert_block(body, info_block(path, meta, ctx["fams"]))
    elif "家族" in path.parts:
        body = insert_block(body, family_block(path, meta, ctx["pf"], ctx["names"]))
    path.write_text("---\n" + "\n".join(hl) + "---\n" + body, encoding="utf-8")


HX_HEAD = re.compile(r"^## 互见\s*$", re.M)
HX_ITEM = re.compile(r"^-\s*(?:\[(?P<loc>[^\]]+)\]\([^)]*\)|(?P<plain>\S.*))\s*$")


def split_huxian(body):
    """把正文中的“## 互见”一节拆出来，返回 (其余正文, [定位符])。"""
    m = HX_HEAD.search(body)
    if not m:
        return body, []
    rest = body[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    sec, after = (rest[:nxt.start()], rest[nxt.start():]) if nxt else (rest, "")
    locs = []
    for line in sec.splitlines():
        mm = HX_ITEM.match(line.strip())
        if mm:
            locs.append((mm["loc"] or mm["plain"]).strip())
    return body[:m.start()].rstrip("\n") + "\n" + after, locs


def huxian_line(path, loc):
    from bodyline import url_for
    t, meta = resolve(loc)
    pn = meta["para"]
    return f"- [{short(loc)}]({url_for(path, meta, pn[0] if isinstance(pn, tuple) else pn)})"


def yaml_without(lines, key):
    """从 YAML 行中去掉某个顶层键及其子行。"""
    out, skip = [], False
    for l in lines:
        if re.match(rf"^{key}:", l):
            skip = True; continue
        if skip and (l.startswith((" ", "-")) or not l.strip()):
            continue
        skip = False
        out.append(l)
    return out


if __name__ == "__main__":
    files = all_files()
    cm = citation_map(files)
    ctx = {"fams": families(), "pf": person_files(), "names": roster()}
    for f in files:
        process(f, cm, ctx)
    print(f"规范化 {len(files)} 个文件")
