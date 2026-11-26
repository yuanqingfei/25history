#!/usr/bin/env bash
# 按 scripts/dibens.tsv 获取主底本（含补卷）到 sources/<书名>/。
# 用法: scripts/fetch_sources.sh              获取 已用书目（被传记引用到的书，见 scripts/used_books.txt）
#       scripts/fetch_sources.sh 全部         获取全部 25 部
#       scripts/fetch_sources.sh 宋史 明史    获取指定的书
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .cache sources

tls() { # $1=KR编号 $2=书名
  D=.cache/tls-texts
  if [ ! -d "$D/.git" ]; then
    git clone -q --depth 1 --filter=blob:none --sparse https://github.com/tls-kr/tls-texts "$D"
    git -C "$D" sparse-checkout set --no-cone "/LICENSE.md"
  fi
  git -C "$D" sparse-checkout add "/data/KR/KR2/KR2a/$1.xml"
  python3 -I scripts/import_tls.py "$D/data/KR/KR2/KR2a/$1.xml" "$2"
}
wiki() { # $1=维基书名 $2=书名 [$3=卷范围]
  if [ ! -d "底本/维基文库/$1" ]; then
    echo "！底本/维基文库/$1 不存在：先在 GitHub Actions 运行“下载维基文库底本”"; return 1
  fi
  python3 -I scripts/import_wikisource.py "$1" "$2" ${3:+--only $3}
}

if [ $# -eq 0 ]; then mapfile -t BOOKS < scripts/used_books.txt
elif [ "$1" = "全部" ]; then mapfile -t BOOKS < <(grep -v '^#' scripts/dibens.tsv | cut -f1)
else BOOKS=("$@"); fi

for b in "${BOOKS[@]}"; do
  line=$(grep -P "^$b\t" scripts/dibens.tsv)
  main=$(echo "$line" | cut -f2); extra=$(echo "$line" | cut -f3)
  case "$main" in
    TLS:*) tls "${main#TLS:}" "$b" ;;
    维基文库:*) wiki "${main#维基文库:}" "$b" ;;
  esac
  if [ -n "$extra" ]; then
    IFS=: read -r _ w rng <<< "$extra"; wiki "$w" "$b" "$rng"
  fi
done
