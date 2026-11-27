# 二十五史人物传

为二十五史（二十四史 + 《清史稿》）中出现的**每一个人**单独立一篇纪传体传记。哪怕此人只出现一句话，也为他立传。

**在线查询：https://yuanqingfei.github.io/25history/**（每次推送后由 GitHub Actions 自动构建）

全部内容用简体中文（底本用繁体精校本，自动转简，繁体原本保留备查）。

核心原则：**传记正文只用史书原文**。只有一个人用到的原文直接写在他的传里；被几个人共用的原文只存一份，传记里写“定位符”（书·卷·段＋起止字），点击即跳到 原文/ 中的对应段落。同一段原文被多人引用时只有一份，由脚本展开成可读的传记。AI 只负责“找、选、排”，不负责“写”。

## 目录

```
人物/<首见书>/<姓名>.md        每人一篇传记
人物/<首见书>/_<篇名>人物表.tsv  按卷整理的人物名单与立传进度
家族/<姓氏>（<郡望>）.md         家族世系
原文/<书>/<卷>.md               底本可浏览版（自动生成，每段带锚点，定位符点击即达）
底本/维基文库/                  由 GitHub Actions 从维基文库下载的原始文件
索引/段落人物.tsv               每段原文涉及哪些人（自动生成）
docs/编写规范.md                传记格式、品评分类、消歧规则
docs/底本说明.md                底本来源与已知问题
scripts/fetch_sources.sh        获取底本到 sources/（不入库）
scripts/find.py                 检索人名，直接给出定位符；“史记+”表示本书及相邻史书
scripts/build_site.py           生成静态网站到 _site/（搜索索引由 Pagefind 生成）
scripts/needed_books.py         列出构建所需的书
scripts/scan.py                 全史扫描：检索首见书之后的全部史书，供整理“后世”一节
scripts/verify.py               校验全部定位符和字段（提交前必须通过）
scripts/render.py               展开成全文传记，输出到 build/
scripts/reanchor.py             规范化引文：独用写原文、共享写定位符，生成链接
scripts/index.py                生成段落→人物反向索引
scripts/build_yuanwen.py        生成 原文/
scripts/import_tls.py           导入 TLS 底本
scripts/migrate.py              更换底本后迁移定位符
scripts/jiaokan.tsv             底本校勘记
scripts/neighbors.tsv           每部书必查的相邻史书
scripts/leizhuan.tsv            类传→默认品评
```

## 用法

```bash
./scripts/fetch_sources.sh                 # 获取已用到的底本（全部：fetch_sources.sh 全部）
python3 scripts/find.py 史记+ 范增 亚父      # 检索史记及相邻的汉书
python3 scripts/verify.py                   # 校验（提交前必须通过）
python3 scripts/render.py                   # 生成可读传记到 build/
python3 scripts/build_yuanwen.py            # 重新生成 原文/
```

## 进度

| 书 | 状态 |
|---|---|
| 史记 | 试点：卷七《项羽本纪》共列出 115 人，已立传 14 人（均已查史记、汉书，并完成全史扫描）；家族 1 个（项氏） |
| 底本 | 25 部主底本已全部确定并可获取（`scripts/dibens.tsv`）：19 部用 TLS 中华书局点校本（其中旧唐书、新唐书、元史缺卷由维基文库补足），周书、宋史、明史、清史稿用维基文库。详见 docs/底本说明.md |

《左传》《国语》《战国策》计划作为“补编”另行处理；《资治通鉴》不作为来源，只用作互见参证。
