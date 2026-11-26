#!/usr/bin/env bash
# 获取底本到 sources/<书名>/NNN.md（每卷一个文件）。来源与已知问题见 docs/底本说明.md。
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .cache sources

wenku() { # $1=书名 $2=wenku仓库名
  [ -d ".cache/$2/.git" ] || git clone -q --depth 1 "https://github.com/wenku/$2" ".cache/$2"
  rm -rf "sources/$1"; mkdir -p "sources/$1"
  cp .cache/"$2"/zh-tw/[0-9]*.md "sources/$1/"
  echo "ok $1 $(ls sources/$1 | wc -l) 卷文件（wenku）"
}
daizhige() { # $1=书名（殆知阁 史藏/正史/ 下的文件名）
  D=.cache/daizhige
  if [ ! -d "$D/.git" ]; then
    git clone -q --depth 1 --filter=blob:none --sparse https://github.com/garychowcmu/daizhigev20 "$D"
    git -C "$D" sparse-checkout set --no-cone "/README.md"
  fi
  git -C "$D" sparse-checkout add "/史藏/正史/$1.txt"
  python3 scripts/import_daizhige.py "$D/史藏/正史/$1.txt" "$1"
}

wenku 史记 shiji
daizhige 汉书     # 临时：简体
