#!/usr/bin/env bash
# ============================================================
# scripts/prepare_defense.sh
# 作用：答辩前一键重置数据库 + 准备「库存不足事务回滚」演示数据
# 环境：Linux VM，~/DataBase，虚拟环境已激活，项目根目录有 .env
# 用法：
#   chmod +x scripts/prepare_defense.sh
#   ./scripts/prepare_defense.sh
# 说明：
#   - init_db.py seed 自带 TRUNCATE ... RESTART IDENTITY，可重复执行，
#     每次都恢复固定的 162165 行（16.2 万）基准数据；
#   - 请在启动 Flask 之前运行本脚本（TRUNCATE 需要独占锁）。
# ============================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

: "${DB_HOST:=127.0.0.1}"
: "${DB_PORT:=5432}"
: "${DB_NAME:=course_db}"
: "${DB_ADMIN_USER:=db_owner}"
: "${DB_ADMIN_PASSWORD:?缺少 DB_ADMIN_PASSWORD，请确认项目根目录 .env 存在且已填写}"
export DB_HOST DB_PORT DB_NAME DB_ADMIN_USER DB_ADMIN_PASSWORD

command -v psql >/dev/null 2>&1 || {
  echo "ERROR: 未找到 psql，请在 Linux VM 上运行本脚本。" >&2
  exit 1
}

echo "[1/3] 重置数据库为初始数据（162165 行 / 16.2 万）..."
python3 scripts/init_db.py seed

echo "[2/3] 设置商品 10 的演示库存 ..."
export PGPASSWORD="$DB_ADMIN_PASSWORD"
PSQL=(psql -X -v ON_ERROR_STOP=1
      -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN_USER" -d "$DB_NAME")

"${PSQL[@]}" -c "UPDATE product SET stock = 5 WHERE product_id = 10;"

# 种子数据里商品有约 5% 概率 is_active=false；下架商品会先返回「商品已下架」
# 而不是「库存不足」，导致演示走不到事务回滚分支，因此一并置为在售。
"${PSQL[@]}" -c "UPDATE product SET is_active = TRUE WHERE product_id = 10;"

# 校验：商品 10 必须存在、库存为 5、且在售（布尔值 psql 输出为 t）
CHECK="$("${PSQL[@]}" -tAc \
  "SELECT stock || '/' || is_active FROM product WHERE product_id = 10;" \
  | tr -d '[:space:]')"
unset PGPASSWORD
if [ "$CHECK" != "5/t" ]; then
  echo "ERROR: 商品 10 校验失败（期望 5/t，实际 '${CHECK}'），请检查种子数据。" >&2
  exit 1
fi

echo "[3/3] 校验总行数 ..."
python3 scripts/init_db.py count

echo "数据库已重置，商品10库存已设为5，可用于演示库存不足事务回滚。"
