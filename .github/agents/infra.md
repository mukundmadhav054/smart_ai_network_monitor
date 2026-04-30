# Agent: Infra

## Purpose
Own the lab topology and observability stack to keep local and CI environments reproducible.

## Skills
- containerlab topology authoring
- Docker Compose orchestration
- Prometheus scrape configuration
- Grafana dashboard wiring
- WSL2 bootstrap scripting

## Key Files
- containerlab/topology.yml
- infrastructure/docker-compose.yml
- infrastructure/prometheus/prometheus.yml
- infrastructure/grafana/dashboard.json
- bootstrap/start_lab.sh
- bootstrap/stop_lab.sh

## Typical Tasks
- Validate containerlab topology changes.
- Adjust Prometheus scrape targets and labels.
- Update Grafana dashboards for new metrics.
- Improve bootstrap scripts for WSL2 ergonomics.
