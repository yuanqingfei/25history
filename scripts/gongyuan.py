"""中国历史纪年 → 公元（儒略历）换算。用寿星天文历（sxtwl）的历史朔望表。
秦及汉初（太初元年即前104年以前）以十月为岁首：某年的十月、十一月、十二月在公历上属于前一年。

用法（命令行）:
  python3 scripts/gongyuan.py <该纪年元年的公元年> <第几年> <月> [闰] [--suishou 10]
  例: 汉三年夏四月（汉元年=前206年，岁首十月）→ python3 scripts/gongyuan.py -206 3 4 --suishou 10
公元年用负数表示公元前（-206 即前206年；内部换算为天文纪年 -205）。
输出该月的公历起止日期。
"""
import argparse
import sxtwl


def astro(y):          # 前206年 → 天文纪年 -205
    return y + 1 if y < 0 else y


def human(y):          # 天文纪年 → “前206年”/“206年”
    return f"前{1 - y}年" if y <= 0 else f"{y}年"


def month_range(yuan_ad, nth, month, leap=False, suishou=1):
    """返回 (起: (年,月,日), 止: (年,月,日)) ，年为天文纪年。"""
    # “第 nth 年”名义上对应的公元年（以正月所在年计）
    y = astro(yuan_ad) + nth - 1
    if suishou == 10:
        # 岁首十月：元年的十月在元年公元年之前一年；名义年号所对应的正月在 y 年
        # 元年=前206 的定义：汉元年冬十月在前207年（天文 -206）年末，正月在前206年（天文 -205）
        if month >= 10:
            y -= 1
    d = sxtwl.fromLunar(y, month, 1, leap)
    # 下一个月初一的前一天
    nd = d.after(29)
    while nd.getLunarDay() != 1:
        nd = nd.after(1)
    end = nd.before(1)
    return ((d.getSolarYear(), d.getSolarMonth(), d.getSolarDay()),
            (end.getSolarYear(), end.getSolarMonth(), end.getSolarDay()))


def fmt(r):
    (y1, m1, d1), (y2, m2, d2) = r
    a = f"{human(y1)}{m1}月{d1}日"
    b = f"{m2}月{d2}日" if y1 == y2 else f"{human(y2)}{m2}月{d2}日"
    return f"{a}—{b}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("yuan", type=int); ap.add_argument("nth", type=int); ap.add_argument("month", type=int)
    ap.add_argument("leap", nargs="?", default=""); ap.add_argument("--suishou", type=int, default=1)
    a = ap.parse_args()
    print(fmt(month_range(a.yuan, a.nth, a.month, a.leap == "闰", a.suishou)))
