#!/usr/bin/env bash
# Деплой с ноутбука одной командой (спросит пароль root один раз):
#   bash infra/scripts/deploy.sh [root@37.139.51.177]
set -euo pipefail
HOST="${1:-root@37.139.51.177}"
cd "$(dirname "$0")/../.."
COPYFILE_DISABLE=1 tar czf - --exclude='__pycache__' backend frontend infra | \
  ssh -o StrictHostKeyChecking=accept-new "$HOST" \
  'rm -rf /opt/shop && mkdir -p /opt/shop && tar xzf - -C /opt/shop && bash /opt/shop/infra/scripts/install.sh 2>&1 | tee /var/log/shop-install.log'
