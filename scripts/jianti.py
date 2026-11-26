"""把 sources/<书名>/ 中导入的繁体底本转成简体工作文本。
- 繁体原样移到 sources/_繁/<书名>/（供校对）；简体写回 sources/<书名>/。
- 用 OpenCC t2s（按词转换），引号「」『』改为“”‘’。
- 必须逐段保持字数不变（繁简字位一一对应，引文位置才能换算）；若某段字数变了，该段改为逐字转换，并报告。
用法: python3 scripts/jianti.py 书名...
"""
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from corpus import SOURCES
import opencc

_C = opencc.OpenCC("t2s")
_Q = str.maketrans({"「": "“", "」": "”", "『": "‘", "』": "’"})


def conv(s: str) -> str:
    t = _C.convert(s).translate(_Q)
    if len(t) != len(s):
        t = "".join(_C.convert(ch) or ch for ch in s).translate(_Q)
        assert len(t) == len(s), s[:20]
        conv.fallback += 1
    return t
conv.fallback = 0


def main(book):
    src, fan = SOURCES / book, SOURCES / "_繁" / book
    if fan.exists():
        shutil.rmtree(fan)
    fan.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(fan))
    src.mkdir()
    n = 0
    for f in sorted(fan.iterdir()):
        if f.suffix == ".md":
            lines = f.read_text(encoding="utf-8").split("\n")
            (src / f.name).write_text("\n".join(conv(l) for l in lines), encoding="utf-8")
            n += 1
        else:
            shutil.copy(f, src / f.name)
    print(f"{book}：{n} 卷转为简体（逐字转换 {conv.fallback} 段）")


if __name__ == "__main__":
    for b in sys.argv[1:]:
        main(b)
