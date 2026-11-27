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
    # 品评依据、互见：旧文件在 YAML 里，迁到正文末尾的列表节（竖排、可点击）
    lists = {}
    for name in LIST_SECTIONS:
        old = [str(x) for x in (meta.pop(name, None) or [])]
        if old:
            hl = yaml_without(hl, name)
        body, cur = split_section(body, name)
        lists[name] = cur + [x for x in old if x not in cur]
    bl = []
    for line in body.split("\n"):
        r = parse_line(line)
        bl.append(format_line(path, r[0], cm) if r else line)
    body = "\n".join(bl).rstrip("\n") + "\n"
    for name in LIST_SECTIONS:
        if lists[name]:
            body += f"\n## {name}\n\n" + "\n".join(section_line(path, name, x) for x in lists[name]) + "\n"
    if "人物" in path.parts:
        body = insert_block(body, info_block(path, meta, ctx["fams"]))
    elif "家族" in path.parts:
        body = insert_block(body, family_block(path, meta, ctx["pf"], ctx["names"]))
    path.write_text("---\n" + "\n".join(hl) + "---\n" + body, encoding="utf-8")


HX_ITEM = re.compile(r"^-\s*(?:\[(?P<loc>[^\]]+)\]\([^)]*\)|(?P<text>.+)〔\[(?P<ref>[^\]｜]+)\]\([^)]*\)〕|(?P<plain>\S.*))\s*$")
LIST_SECTIONS = ["品评依据", "互见"]          # 正文末尾的列表节，按此顺序排列


def item_loc(m):
    if m["loc"]:
        return m["loc"].strip()
    if m["ref"]:
        return f"{m['ref']}｜{m['text']}"
    return m["plain"].strip()


def split_huxian(body):
    return split_section(body, "互见")


def split_section(body, name):
    """把正文中的“## <name>”一节拆出来，返回 (其余正文, [定位符])。"""
    m = re.compile(rf"^## {name}\s*$", re.M).search(body)
    if not m:
        return body, []
    rest = body[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    sec, after = (rest[:nxt.start()], rest[nxt.start():]) if nxt else (rest, "")
    locs = []
    for line in sec.splitlines():
        mm = HX_ITEM.match(line.strip())
        if mm:
            locs.append(item_loc(mm))
    return body[:m.start()].rstrip("\n") + "\n" + after, locs


def pingping_line(path, loc):
    """品评依据：显示原文全文＋出处链接。"""
    from bodyline import url_for
    t, meta = resolve(loc)
    pn = meta["para"]
    lo, hi = pn if isinstance(pn, tuple) else (pn, pn)
    ps = f"{lo}-{hi}" if hi > lo else f"{lo}"
    return f"- {t}〔[{meta['book']}·{meta['juan']}·{ps}]({url_for(path, meta, lo)})〕"


def section_line(path, name, loc):
    return pingping_line(path, loc) if name == "品评依据" else huxian_line(path, loc)


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
