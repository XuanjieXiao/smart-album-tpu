#!/usr/bin/env bash
# ------------------------------------------------------------
# deploy_to_album.sh
# 作用：把当前工作目录中的指定文件 / 目录复制到
#       /data/xuanjiexiao/SmartAlbumFiles/AlbumForSearch
#      （目标不存在时自动创建，已存在时覆盖）
# ------------------------------------------------------------
set -euo pipefail

# 源目录 —— 脚本所在位置
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 目标目录
DST_DIR="/data/xuanjiexiao/SmartAlbumFiles/AlbumForSearch"

# 需要复制的单独文件
FILES=(
  "app.py"
  "bce_service.py"
  "database_utils.py"
  "faiss_utils.py"
  "qwen_service.py"
  "README.md"
  "qwen_servicecopy.py"
  "qwen_service—save.py"
)

# 需要复制的目录（连同内部所有内容）
DIRS=(
  "static"
  "templates"
)

echo ">>> 正在同步到 $DST_DIR"
mkdir -p "$DST_DIR"

# 1. 复制文件
for f in "${FILES[@]}"; do
  if [[ -f "$SRC_DIR/$f" ]]; then
    echo "    拷贝文件 $f"
    cp -f "$SRC_DIR/$f" "$DST_DIR/"
  else
    echo "    [警告] 未找到文件 $f" >&2
  fi
done

# 2. 复制目录（使用 rsync 可以保持权限并删除目标目录里已被源目录删掉的文件）
for d in "${DIRS[@]}"; do
  if [[ -d "$SRC_DIR/$d" ]]; then
    echo "    同步目录 $d/"
    rsync -a --delete "$SRC_DIR/$d/" "$DST_DIR/$d/"
  else
    echo "    [警告] 未找到目录 $d/" >&2
  fi
done

echo ">>> 同步完成"
