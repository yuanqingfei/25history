"""校验 人物/ 与 家族/ 下的全部文件。规则见 docs/编写规范.md。
- 正文只允许标题行、空行和“> 定位符”行；每个定位符必须能在底本中展开。
- YAML 头中的 品评依据、互见、家族成员依据 等列表里的定位符同样必须能展开。
- 枚举字段取值合法；类传归属 与 品评 的对应关系见 scripts/leizhuan.tsv。
用法: python3 scripts/verify.py [文件或目录 ...]
"""
import sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT
from refs import resolve, RefError, REF
from bodyline import parse_line, format_line, citation_map, is_shared
CM = citation_map()

REQUIRED = ["id", "姓名", "身份", "品评", "品评依据类型", "出现卷", "校对状态"]
身份 = {"帝王", "国王", "后妃", "宗室", "臣属", "将领", "士民", "妇女", "四夷", "方外", "其他"}
品评 = {"君子", "普通", "小人", "恶贼"}
依据类型 = ["类传归属", "史臣论赞", "史家叙评", "书中人物评语", "行事推断", "无"]
LEIZHUAN = {}
for ln in (ROOT / "scripts" / "leizhuan.tsv").read_text(encoding="utf-8").splitlines():
    if ln and not ln.startswith("#"):
        k, v = ln.split("\t")[:2]
        LEIZHUAN[k] = v


KNOWN_IDS = {}
for t in (ROOT / "人物").rglob("_*人物表.tsv"):
    for ln in t.read_text(encoding="utf-8").splitlines()[1:]:
        c = ln.split("\t")
        KNOWN_IDS[c[0]] = c[1]


def refs_in(obj):
    """递归取出 YAML 中所有像定位符的字符串。"""
    if isinstance(obj, str):
        if REF.match(obj.strip()):
            yield obj
    elif isinstance(obj, list):
        for x in obj:
            yield from refs_in(x)
    elif isinstance(obj, dict):
        for x in obj.values():
            yield from refs_in(x)


def check(ref, where, errs):
    try:
        resolve(ref)
    except RefError as e:
        errs.append(f"{where}: {e}")


def check_body_line(path, s, where, errs):
    """引文行必须是规范写法（独用段落写原文，共享段落写定位符），且链接正确。"""
    loc, url, form = parse_line(s)
    check(loc, where, errs)
    try:
        expect = format_line(path, loc, CM)
    except RefError:
        return
    if s.strip() != expect:
        kind = "共享引文应写定位符" if is_shared(loc, CM, path) else "独用引文应直接写原文"
        errs.append(f"{where}: 写法不规范（{kind}；运行 scripts/reanchor.py 自动修正）")
    elif not (path.resolve().parent / url.split("#")[0]).exists():
        errs.append(f"{where}: 链接目标不存在（运行 scripts/build_yuanwen.py 生成 原文/）")


def verify_person(path, meta, body, errs):
    for k in REQUIRED:
        if k not in meta:
            errs.append(f"{path}: 缺少字段 {k}")
    if meta.get("身份") not in 身份:
        errs.append(f"{path}: 身份取值不合法 {meta.get('身份')}")
    if meta.get("品评") not in 品评:
        errs.append(f"{path}: 品评取值不合法 {meta.get('品评')}")
    t = meta.get("品评依据类型")
    if t not in 依据类型:
        errs.append(f"{path}: 品评依据类型不合法 {t}")
    if t == "无" and meta.get("品评") != "普通":
        errs.append(f"{path}: 依据类型为“无”时品评只能是普通")
    if t != "无" and not meta.get("品评依据"):
        errs.append(f"{path}: 缺少品评依据")
    lz = meta.get("类传")
    if lz:
        if lz not in LEIZHUAN:
            errs.append(f"{path}: 类传 {lz} 不在 scripts/leizhuan.tsv 中")
        elif t != "类传归属":
            errs.append(f"{path}: 有类传时品评依据类型应为“类传归属”")
        elif meta.get("品评") != LEIZHUAN[lz] and "改判" not in (meta.get("备注") or ""):
            errs.append(f"{path}: 类传 {lz} 默认品评为 {LEIZHUAN[lz]}，若改判须在备注中写“改判”及理由")
    if t == "行事推断" and not meta.get("推断理由"):
        errs.append(f"{path}: 品评依据类型为“行事推断”时必须填写“推断理由”")
    n = 0
    for no, line in enumerate(body.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if not s.startswith(">"):
            errs.append(f"{path} 正文第{no}行: 不是引文行（正文只能放原文）")
            continue
        n += 1
        check_body_line(path, s, f"{path} 正文第{no}行", errs)
    if n == 0:
        errs.append(f"{path}: 正文没有引文")


def verify_file(path):
    errs = []
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        return [f"{path}: 缺少 YAML 头"]
    _, head, body = raw.split("---\n", 2)
    meta = yaml.safe_load(head)
    for r in refs_in(meta):
        check(r, f"{path} YAML", errs)
    if "人物" in path.parts:
        verify_person(path, meta, body, errs)
    if "家族" in path.parts:
        for mem in meta.get("成员") or []:
            if mem.get("id") not in KNOWN_IDS:
                errs.append(f"{path}: 成员 {mem.get('姓名')} 的编号 {mem.get('id')} 不在任何人物表中")
            elif KNOWN_IDS[mem["id"]] != mem.get("姓名"):
                errs.append(f"{path}: 编号 {mem['id']} 在人物表中是 {KNOWN_IDS[mem['id']]}，不是 {mem.get('姓名')}")
    for no, line in enumerate(body.splitlines(), 1):
        s = line.strip()
        if "家族" in path.parts and s and not s.startswith(("#", ">")):
            errs.append(f"{path} 正文第{no}行: 不是定位符行")
        elif "家族" in path.parts and s.startswith(">"):
            check_body_line(path, s, f"{path} 正文第{no}行", errs)
    return errs


def main(args):
    targets = [Path(a) for a in args] or [ROOT / "人物", ROOT / "家族"]
    files = []
    for t in targets:
        if t.is_dir():
            files += sorted(p for p in t.rglob("*.md") if not p.name.startswith(("_", "README")))
        elif t.exists():
            files.append(t)
    errs = [e for f in files for e in verify_file(f)]
    print("\n".join(errs + [f"校验 {len(files)} 个文件，错误 {len(errs)} 处"]))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
