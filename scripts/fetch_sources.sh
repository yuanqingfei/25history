#!/usr/bin/env bash
# 获取底本到 sources/<书名>/NNN.md（每卷一个文件）。主底本与备选底本见 docs/底本说明.md。
# 用法: scripts/fetch_sources.sh            获取当前已启用的主底本
#       scripts/fetch_sources.sh 备选        另外获取备选底本到 sources/_备/
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .cache sources

tls() { # $1=KR编号 $2=书名 —— TLS（tls-kr/tls-texts，中华书局点校本，CC BY-SA 4.0）
  D=.cache/tls-texts
  if [ ! -d "$D/.git" ]; then
    git clone -q --depth 1 --filter=blob:none --sparse https://github.com/tls-kr/tls-texts "$D"
    git -C "$D" sparse-checkout set --no-cone "/LICENSE.md"
  fi
  git -C "$D" sparse-checkout add "/data/KR/KR2/KR2a/$1.xml"
  python3 -I scripts/import_tls.py "$D/data/KR/KR2/KR2a/$1.xml" "$2"
}
wenku() { # $1=目标目录 $2=wenku仓库名 —— 维基文库整理本
  [ -d ".cache/$2/.git" ] || git clone -q --depth 1 "https://github.com/wenku/$2" ".cache/$2"
  rm -rf "sources/$1"; mkdir -p "sources/$1"; cp .cache/"$2"/zh-tw/[0-9]*.md "sources/$1/"
  echo "ok $1（wenku）"
}
daizhige() { # $1=书名 $2=目标目录 —— 殆知阁（简体）
  D=.cache/daizhige
  if [ ! -d "$D/.git" ]; then
    git clone -q --depth 1 --filter=blob:none --sparse https://github.com/garychowcmu/daizhigev20 "$D"
    git -C "$D" sparse-checkout set --no-cone "/README.md"
  fi
  git -C "$D" sparse-checkout add "/史藏/正史/$1.txt"
  python3 -I scripts/import_daizhige.py "$D/史藏/正史/$1.txt" "$2"
}

# —— 主底本（已启用）——
tls KR2a0001 史记
tls KR2a0007 汉书

# —— 备选底本 ——
if [ "${1:-}" = "备选" ]; then
  wenku _备/史记 shiji
  daizhige 汉书 _备/汉书
fi
