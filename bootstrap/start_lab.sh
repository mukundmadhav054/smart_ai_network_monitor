#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="infrastructure/docker-compose.yml"
TOPOLOGY_FILE="containerlab/topology.yml"

if [[ -f .env]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

wait_for_http() {
    local url="$1"
    local retries="${2:-30}"
    local delay="${3:-2}"

    for ((i=1; i<=retries; i++)); do
      if curl -fsS "$url" >/dev/null 2>&1; then
        echo "Healthy: $url"
        return 0
      fi
      echo "Waiting ($i/$retries) for $url"
      sleep "$delay"
    done

    echo "Timed out waiting for $url"
    return 1
}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required but not found"
  exit 1
fi

if ! command -v containerlab >/dev/null 2>&1; then
  echo "containerlab is required but not found"
  exit 1
fi

echo "Starting Prometheus + Grafana"
docker compose -f "$COMPOSE_FILE" up -d

if [[ "$EUID" -eq 0 ]]; then
  CLAB_CMD=(containerlab)
else
  CLAB_CMD=(sudo -E containerlab)
fi

echo "Deploying containerlab topology"
"${CLAB_CMD[@]}" deploy -t "$TOPOLOGY_FILE" --reconfigure

wait_for_http "http://localhost:9090/-/healthy" 40 2
wait_for_http "http://localhost:3000/api/health" 40 2

echo "Lab setup completed and is up."
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3000"
