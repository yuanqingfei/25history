"""底本更换后，把传记中的定位符迁移到新底本。
做法：用旧底本展开每个定位符得到原文，在新底本同一卷中做“去标点、繁转简”后的匹配，
找到对应位置后按新底本原文重新生成定位符。精确匹配失败时做模糊匹配（覆盖率≥0.85），
仍失败的列出来人工处理。
用法: python3 scripts/migrate.py <旧底本目录名> <新底本目录名> <书名> 文件...
例:   python3 scripts/migrate.py _old_史记 史记 史記 人物/史记/*.md
"""
import re, sys, difflib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import corpus, refs
import opencc
T2S = opencc.OpenCC("t2s")
PUN = re.compile(r"[\s，。、；：？！「」『』“”‘’（）()【】〔〕《》〈〉…—·．､\[\]{}]")

def norm_map(s):
    """返回 (规范化字符串, 每个规范化字符在原串中的下标)。逐字转换以保持对应。"""
    out, idx = [], []
    for i, ch in enumerate(s):
        if PUN.match(ch):
            continue
        out.append(T2S.convert(ch)[:1] or ch); idx.append(i)
    return "".join(out), idx

old_dir, new_dir, fan = sys.argv[1], sys.argv[2], sys.argv[3]
LOC = re.compile(r"(?<![^\s>\-])" + re.escape(fan) + r"·\d+[^·｜\s]*·\d+｜[^\n\"']+")
fails = []

def relocate(loc):
    _, juan, pn, body = refs.parse(loc)
    old_p = corpus.juan_paras(old_dir, juan)[pn - 1]
    refs.BOOKS[fan] = dict(refs.BOOKS[fan], name=old_dir)
    text, _ = refs.resolve(loc)
    refs.BOOKS[fan] = dict(refs.BOOKS[fan], name=new_dir)
    q, _ = norm_map(text)
    paras = corpus.juan_paras(new_dir, juan)
    best = None
    for k, p in enumerate(paras, 1):
        n, idx = norm_map(p)
        i = n.find(q)
        if i >= 0:
            best = (1.0, k, idx[i], idx[i + len(q) - 1] + 1); break
        sm = difflib.SequenceMatcher(None, q, n, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size > 0]
        if not blocks:
            continue
        cov = sum(b.size for b in blocks) / len(q)
        if cov >= 0.85 and (best is None or cov > best[0]):
            head = blocks[0].a                                  # 开头没对上的字数（异体字等）
            tail = len(q) - (blocks[-1].a + blocks[-1].size)    # 结尾没对上的字数
            b0 = max(blocks[0].b - head, 0)
            b1 = min(blocks[-1].b + blocks[-1].size - 1 + tail, len(idx) - 1)
            best = (cov, k, idx[b0], idx[b1] + 1)
    if not best:
        fails.append(loc); return loc
    cov, k, s, e = best
    p = paras[k - 1]
    while e < len(p) and PUN.match(p[e]) and p[e] not in "「『“（(【〔《〈":  # 带上句末标点
        e += 1
    new = p[s:e]
    if cov < 1.0:
        print(f"  模糊匹配 {cov:.2f}: {text[:20]} → {new[:20]}")
    return refs.make(fan, juan, k, p, new)

for f in map(Path, sys.argv[4:]):
    s = f.read_text(encoding="utf-8")
    f.write_text(LOC.sub(lambda m: relocate(m[0]), s), encoding="utf-8")
print("失败:", len(fails)); [print("  ", x) for x in fails]
