# 底本原始文件

这里存放无法在开发环境中直接下载、由 GitHub Actions 抓取的底本原始文件。`scripts/fetch_sources.sh` 会从这里导入到 `sources/`。

## 维基文库/

由工作流 `.github/workflows/fetch-wikisource.yml`（脚本 `scripts/fetch_wikisource.py`）从 [维基文库](https://zh.wikisource.org/) 下载。每部书一个目录，每卷一个文件；`manifest.tsv` 记录每个页面的标题、修订号（revid）、抓取时间和网址。

内容依维基文库的授权（CC BY-SA 4.0）发布。改动仅限于：去掉页眉、导航、编辑链接、注释和参考文献，把网页段落转成纯文本。
