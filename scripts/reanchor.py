"""把文件中所有定位符按当前规则重新生成（展开后的原文不变）。用法: python3 scripts/reanchor.py 文件...
用于调整锚点长度，或底本修订后重算段号以外的锚点。"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from refs import REF, resolve, make, _paras
LOC = re.compile(r"(?<![^\s>\-])[^\s\"'\[\],>]+·\d+[^·｜\s]*·\d+｜[^\n\"']+")
for f in map(Path, sys.argv[1:]):
    s = f.read_text(encoding="utf-8")
    def rep(m):
        t, meta = resolve(m[0])
        return make(meta["book"], meta["juan"], meta["para"], _paras(meta["name"], meta["juan"])[meta["para"] - 1], t)
    f.write_text(LOC.sub(rep, s), encoding="utf-8")
