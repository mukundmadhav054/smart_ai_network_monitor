#!usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd ROOT_DIR

COMPOSE_FILE="infrastructure/docker-compose.yml"
TOPOLOGY_FILE="containerlab/topology.yml"

echo "Stopping observability stack"
if command -v docker >/dev/null 2>&1; then
  docker compose -f "$COMPOSE_FILE" down
fi

echo "Destroying containerlab topology"
if command -v containerlab >/dev/null 2>&1; then
  if [[ "$EUID" -eq 0 ]]; then
    containerlab destroy -t "$TOPOLOGY_FILE" --cleanup || true
  else
    sudo -E containerlab destroy -t "$TOPOLOGY_FILE" --cleanup || true
  fi
fi

echo "Lab stopped."
