#!/usr/bin/env bash
# Полная установка магазина на чистый Ubuntu 24.04 (запускать от root):
#   bash infra/scripts/install.sh
# Скрипт можно запускать повторно — он доустановит недостающее и обновит приложение.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ADMIN_TOKEN="${ADMIN_TOKEN:-IronRiff-2026}"
K="microk8s kubectl"
step() { echo -e "\n\033[1;31m==> $*\033[0m"; }

step "1/7 Swap 1 ГБ (на сервере всего 2 ГБ RAM и 10 ГБ диска)"
if ! swapon --show | grep -q /swapfile; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  grep -q /swapfile /etc/fstab || echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

step "2/7 MicroK8s"
if ! command -v microk8s >/dev/null; then
  snap install microk8s --classic --channel=1.31/stable
fi
microk8s status --wait-ready >/dev/null
microk8s enable dns hostpath-storage ingress helm3
# Диск маленький: снижаем порог, при котором kubelet начинает выселять поды и удалять образы
ARGS=/var/snap/microk8s/current/args/kubelet
if ! grep -q "nodefs.available<300Mi" "$ARGS"; then
  sed -i '/^--eviction-hard/d' "$ARGS"
  echo '--eviction-hard="memory.available<100Mi,nodefs.available<300Mi,imagefs.available<300Mi"' >> "$ARGS"
  printf -- '--image-gc-high-threshold=97\n--image-gc-low-threshold=95\n' >> "$ARGS"
  snap restart microk8s.daemon-kubelite && microk8s status --wait-ready >/dev/null
fi
# containerd: не хранить сжатые слои после распаковки (экономит ~1 ГБ);
# unpigz из пакета pigz нужен containerd для распаковки образов
command -v unpigz >/dev/null || (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq pigz)
TPL=/var/snap/microk8s/current/args/containerd-template.toml
if ! grep -q discard_unpacked_layers "$TPL"; then
  sed -i '/\[plugins."io.containerd.grpc.v1.cri".containerd\]/a\    discard_unpacked_layers = true' "$TPL"
  snap restart microk8s.daemon-containerd
fi
apt-get clean

step "3/7 Docker (только для сборки образов)"
command -v docker >/dev/null || (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq docker.io)
systemctl start docker

step "4/7 Сборка образов и импорт в containerd MicroK8s"
docker build -q -t shop-backend:1.0 "$ROOT/backend"
docker build -q -t shop-frontend:1.0 "$ROOT/frontend"
docker save shop-backend:1.0 shop-frontend:1.0 | microk8s ctr image import - >/dev/null
docker system prune -af >/dev/null && systemctl stop docker docker.socket   # освобождаем диск и память

step "5/7 Crunchy Postgres Operator"
if ! microk8s helm3 status pgo -n postgres-operator >/dev/null 2>&1; then
  microk8s helm3 install pgo oci://registry.developers.crunchydata.com/crunchydata/pgo \
    -n postgres-operator --create-namespace --wait
fi

step "6/7 Манифесты приложения"
$K apply -f "$ROOT/infra/k8s/00-namespace.yaml"
$K -n shop create secret generic shop-admin --from-literal=token="$ADMIN_TOKEN" \
  --dry-run=client -o yaml | $K apply -f -
$K apply -f "$ROOT/infra/k8s/"
echo "Ждём, пока оператор создаст базу..."
until $K -n shop get secret shop-db-pguser-shop >/dev/null 2>&1; do sleep 5; done
$K -n shop rollout restart deployment backend frontend
$K -n shop rollout status deployment backend --timeout=600s
$K -n shop rollout status deployment frontend --timeout=300s

step "7/7 Проверка"
$K -n shop get pods -o wide
sleep 3
curl -s http://127.0.0.1/api/health && echo
echo -e "\n\033[1;32mГотово! Магазин: http://$(hostname -I | awk '{print $1}')/  токен админки: $ADMIN_TOKEN\033[0m"
