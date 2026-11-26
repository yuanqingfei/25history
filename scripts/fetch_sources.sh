#!/usr/bin/env bash
# 获取底本到 sources/<书名>/NNN.md（每卷一个文件）。
# 当前：史记取自 github.com/wenku（维基文库整理，繁体，分卷完整）。
# 其他各史的底本尚未选定，见 docs/底本说明.md。
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .cache sources
get() { # $1=书名 $2=wenku仓库名
  [ -d ".cache/$2/.git" ] || git clone -q --depth 1 "https://github.com/wenku/$2" ".cache/$2"
  rm -rf "sources/$1"; mkdir -p "sources/$1"
  cp .cache/"$2"/zh-tw/[0-9]*.md "sources/$1/"
  echo "ok $1 $(ls sources/$1 | wc -l) 卷文件"
}
get 史记 shiji
