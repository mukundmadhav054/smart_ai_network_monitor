#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[1/6] Checking WSL environment"
if ! grep -qi "microsoft" /proc/version; then
  echo "Warning: This script is tuned for WSL2, but continuing execution."
fi

echo "[2/6] Installing system dependencies"
sudo apt-get update
sudo apt-get install -y \
  ca-certificates curl git jq make \
  python3 python3-venv python3-pip \
  iproute2 iperf3

echo "[3/6] Checking containerlab"
if ! command -v containerlab >/dev/null 2>&1; then
  echo "Installing containerlab..."
  bash -c "$(curl -sL https://get.containerlab.dev)"
else
  echo "containerlab already installed"
fi

echo "[4/6] Preparing Python virtual environment"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel

echo "[5/6] Installing Python tooling"
if [[ -f api/requirements.txt ]]; then
  pip install -r api/requirements.txt
fi
pip install "ansible-core>=2.14,<2.18" ansible-lint pytest ruff

echo "[6/6] Applying executable bits"
chmod +x bootstrap/*.sh || true
chmod +x simulator/*.sh 2>/dev/null || true

if command -v docker >/dev/null 2>&1; then
  if ! docker ps >/dev/null 2>&1; then
    echo "Docker is installed but not accessible to current user."
    echo "If needed: sudo usermod -aG docker $USER && newgrp docker"
  fi
else
  echo "Docker CLI not found. Install Docker Desktop with WSL2 integration."
fi

echo "Bootstrap complete."
echo "Next steps:"
echo "  cp .env.example .env"
echo "  ./bootstrap/start_lab.sh"