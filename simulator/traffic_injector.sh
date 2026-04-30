#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-incident}"
TOPOLOGY_NAME="smart-ai-network-monitor"
CONTAINER="clab-${TOPOLOGY_NAME}-host1"
INTERFACE="${2:-eth1}"

case "$ACTION" in
  incident)
    docker exec "$CONTAINER" tc qdisc replace dev "$INTERFACE" root netem delay 120ms loss 5%
    ;;
  clear)
    docker exec "$CONTAINER" tc qdisc del dev "$INTERFACE" root || true
    ;;
  status)
    docker exec "$CONTAINER" tc qdisc show dev "$INTERFACE"
    ;;
  *)
    echo "Usage: $0 {incident|clear|status} [interface]"
    exit 1
    ;;
esac
