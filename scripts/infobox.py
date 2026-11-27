"""根据 YAML 自动生成的两种区块（不要手改，reanchor.py 会重写，verify.py 会检查）：

1. 人物传记标题下的“信息栏”：生、卒（公元）、身份、品评、家族（链接）。
2. 家族文件的“世系图”（Mermaid，GitHub 直接显示为树状图）与成员表（链接到各人传记）。

家族归属只在家族文件的“成员”里登记；人物信息栏中的家族链接由此反查生成。
"""
import os, re
from pathlib import Path
import yaml
from corpus import ROOT

BEGIN, END = "<!-- 自动生成：开始（勿手改，运行 scripts/reanchor.py 更新） -->", "<!-- 自动生成：结束 -->"
BLOCK = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.S)


def load_meta(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8").split("---\n", 2)[1])


def person_files():
    """{id: 文件路径}"""
    out = {}
    for p in (ROOT / "人物").rglob("*.md"):
        if not p.name.startswith("_"):
            out[load_meta(p)["id"]] = p
    return out


def roster():
    """{id: 姓名}，来自各卷人物表"""
    out = {}
    for t in (ROOT / "人物").rglob("_*人物表.tsv"):
        for ln in t.read_text(encoding="utf-8").splitlines()[1:]:
            c = ln.split("\t"); out[c[0]] = c[1]
    return out


def families():
    """[(家族文件, meta)]"""
    return [(p, load_meta(p)) for p in sorted((ROOT / "家族").glob("*.md"))]


def rel(src: Path, dst: Path):
    return os.path.relpath(dst, src.resolve().parent).replace(os.sep, "/")


def _date(d):
    return (d or {}).get("公元") or "" if isinstance(d, dict) else (d or "")


def info_block(path: Path, meta, fams=None):
    fams = families() if fams is None else fams
    sz = meta.get("生卒") or {}
    links = [f"[{fm['家族']}（{fm.get('郡望', '')}）]({rel(path, fp)})".replace("（）", "")
             for fp, fm in fams if any(m.get("id") == meta["id"] for m in fm.get("成员") or [])]
    row = [_date(sz.get("生")), _date(sz.get("卒")), meta.get("身份", ""), meta.get("品评", ""), "、".join(links) or "—"]
    return "\n".join([BEGIN, "", "| 生 | 卒 | 身份 | 品评 | 家族 |", "|---|---|---|---|---|",
                      "| " + " | ".join(row) + " |", "", END]) + "\n"


def family_block(path: Path, meta, pf=None, names=None):
    pf = person_files() if pf is None else pf
    names = roster() if names is None else names
    mem = meta.get("成员") or []
    root = "ROOT"
    lines = ["```mermaid", "graph TD", f'  {root}(["{meta["家族"]}（{meta.get("郡望", "")}）"])']
    nid = lambda i: "N" + re.sub(r"\W", "_", i)
    for m in mem:
        label = m["姓名"] + (f"<br/>第{m['世代']}代" if str(m.get("世代", "")).isdigit() else "")
        lines.append(f'  {nid(m["id"])}["{label}"]')
    ids = {m["id"] for m in mem}
    linked = {r.get("对象") for m in mem for r in (m.get("其他关系") or [])}
    for m in mem:
        if m.get("父") in ids:
            lines.append(f'  {nid(m["父"])} --> {nid(m["id"])}')
        elif m.get("母") in ids:
            lines.append(f'  {nid(m["母"])} --> {nid(m["id"])}')
        elif m["id"] not in linked:
            lines.append(f'  {root} -.-> {nid(m["id"])}')
        for r in m.get("其他关系") or []:
            if r.get("对象") in ids:
                lines.append(f'  {nid(m["id"])} -. {r["关系"]} .-> {nid(r["对象"])}')
    lines.append("```")
    table = ["| 世代 | 成员 | 关系 |", "|---|---|---|"]
    for m in sorted(mem, key=lambda m: (not str(m.get("世代", "")).isdigit(), str(m.get("世代", "")).zfill(3))):
        p = pf.get(m["id"])
        name = f"[{m['姓名']}]({rel(path, p)})" if p else f"{m['姓名']}（未立传）"
        table.append(f"| {m.get('世代', '')} | {name} | {m.get('关系', '')} |")
    return "\n".join([BEGIN, "", "## 世系图", ""] + lines + ["", "## 成员", ""] + table + ["", END]) + "\n"


def insert_block(body: str, block: str):
    """把自动生成区块放在第一个“# 标题”行之后（已有则替换）。"""
    body = BLOCK.sub("", body)
    m = re.search(r"^# .*\n", body, re.M)
    i = m.end() if m else 0
    return body[:i] + "\n" + block + "\n" + body[i:].lstrip("\n")


def strip_block(body: str):
    return BLOCK.sub("", body)
