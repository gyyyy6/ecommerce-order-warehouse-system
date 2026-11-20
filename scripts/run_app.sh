#!/usr/bin/env bash
# ============================================================
# scripts/run_app.sh
# 作用：在 Linux VM 上启动 Flask，绑定 0.0.0.0:5000，关闭 debug/reloader。
# 使用：
#   chmod +x scripts/run_app.sh
#   ./scripts/run_app.sh
# 说明：
#   - 如果项目根目录有 .env，会加载其中的环境变量；
#   - .env 不得提交仓库；
#   - 生产演示建议用 systemd 托管，最终仍绑定 0.0.0.0:5000。
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

export FLASK_DEBUG=0

exec python3 -m flask \
  --app app \
  run \
  --host "${FLASK_HOST:-0.0.0.0}" \
  --port "${FLASK_PORT:-5000}" \
  --no-debugger \
  --no-reload