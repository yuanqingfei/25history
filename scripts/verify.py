"""逐字校验传记文件。

规则（见 docs/编写规范.md）：
1. 文件以 YAML 头开始，必填字段齐全，枚举字段取值合法。
2. 正文（YAML 头之后）只允许：标题行（# 开头）、空行、引文行。
3. 引文行格式：> 原文〔書名·卷N·篇名〕
   原文必须是该卷底本中的一段连续文字（只忽略空白，标点、字形必须一致）。
4. YAML 头中“品评依据”的每一条也必须是同样格式的引文，同样校验。

用法: python3 scripts/verify.py [文件或目录 ...]   默认校验 人物/ 下全部 .md
退出码非 0 表示有错误。
"""
import re, sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent))
from corpus import ROOT, load_books, juan_text, norm

QUOTE = re.compile(r"^>\s*(?P<text>.+?)\s*〔(?P<book>[^·〕]+)·卷(?P<juan>\d+)·(?P<pian>[^〕]+)〕\s*$")
REF = re.compile(r"^(?P<text>.+?)\s*〔(?P<book>[^·〕]+)·卷(?P<juan>\d+)·(?P<pian>[^〕]+)〕\s*$")
REQUIRED = ["id", "姓名", "身份", "品评", "品评依据类型", "出现卷", "校对状态"]
身份 = {"帝王", "国王", "后妃", "宗室", "臣属", "将领", "士民", "妇女", "四夷", "方外", "其他"}
品评 = {"君子", "普通", "小人", "恶贼"}
依据类型 = {"史臣论赞", "类传归属", "史家叙评", "书中人物评语", "行事推断", "无"}

BOOKS = load_books()
_cache = {}


def check_quote(m, where, errs):
    book = BOOKS.get(m["book"])
    if not book:
        errs.append(f"{where}: 未知书名 {m['book']}")
        return
    key = (book["name"], int(m["juan"]))
    if key not in _cache:
        try:
            _cache[key] = norm(juan_text(*key))
        except FileNotFoundError:
            errs.append(f"{where}: 找不到底本 {key}（先运行 scripts/fetch_sources.sh）")
            return
    if norm(m["text"]) not in _cache[key]:
        errs.append(f"{where}: 原文不符 → {m['text'][:40]}")


def verify_file(path: Path):
    errs = []
    raw = path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        return [f"{path}: 缺少 YAML 头"]
    _, head, body = raw.split("---\n", 2)
    meta = yaml.safe_load(head)
    for k in REQUIRED:
        if k not in meta:
            errs.append(f"{path}: 缺少字段 {k}")
    if meta.get("身份") not in 身份:
        errs.append(f"{path}: 身份取值不合法 {meta.get('身份')}")
    if meta.get("品评") not in 品评:
        errs.append(f"{path}: 品评取值不合法 {meta.get('品评')}")
    if meta.get("品评依据类型") not in 依据类型:
        errs.append(f"{path}: 品评依据类型不合法 {meta.get('品评依据类型')}")
    for i, ref in enumerate(meta.get("品评依据") or []):
        m = REF.match(ref.strip())
        if not m:
            errs.append(f"{path}: 品评依据第{i+1}条格式错误")
        else:
            check_quote(m, f"{path} 品评依据{i+1}", errs)
    n = 0
    for ln_no, line in enumerate(body.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = QUOTE.match(s)
        if not m:
            errs.append(f"{path} 正文第{ln_no}行: 不是引文行（正文只能放原文）")
            continue
        n += 1
        check_quote(m, f"{path} 正文第{ln_no}行", errs)
    if n == 0:
        errs.append(f"{path}: 正文没有引文")
    return errs


def main(args):
    targets = [Path(a) for a in args] or [ROOT / "人物"]
    files = []
    for t in targets:
        files += sorted(t.rglob("*.md")) if t.is_dir() else [t]
    files = [f for f in files if not f.name.startswith(("README", "_"))]
    all_errs = []
    for f in files:
        all_errs += verify_file(f)
    for e in all_errs:
        print(e)
    print(f"校验 {len(files)} 个文件，错误 {len(all_errs)} 处")
    return 1 if all_errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
