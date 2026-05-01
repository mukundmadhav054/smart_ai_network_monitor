# Smart AI Network Monitor (MVP)

Smart AI Network Monitor is an opinionated, minimal, open-source scaffold for network automation engineers.

Core pipeline:
Telemetry ingestion -> anomaly detection -> intent mapping -> safe Ansible remediation

This repository is designed for:
- Windows developers using WSL2
- containerlab with FRR routers
- Prometheus and Grafana observability
- FastAPI service for alerts and remediation triggering

## MVP Scope

- One topology: r1, r2 (FRR), host1 traffic generator
- Synthetic telemetry generator
- One detector: rolling z-score with IsolationForest fallback
- YAML intent store
- One remediation playbook with:
  - dry_run
  - canary
  - rollback
- CI for lint, unit tests, ansible-lint

## Architecture

~~~mermaid
graph LR
    TG[Telemetry Generator] -->|/metrics| PROM[Prometheus]
    PROM -->|PromQL| API[FastAPI Service]
    API --> DET[Anomaly Detector]
    API --> INTENT[Intent Store YAML]
    API -->|safe invoke| ANS[Ansible Playbook]
    ANS --> LAB[containerlab FRR Topology]
    PROM --> GRAF[Grafana Dashboard]
~~~

## Workflow Guide

For a full end-to-end walkthrough, see [docs/USAGE.md](docs/USAGE.md).

### Workflow Flowchart

~~~mermaid
flowchart TD
  A[Bootstrap WSL2 environment] --> B[Start Prometheus + Grafana]
  B --> C[Deploy containerlab topology]
  C --> D[Run telemetry simulator]
  D --> E[Run API service]
  E --> F[Check alerts endpoint]
  F --> G{Anomaly detected?}
  G -->|No| D
  G -->|Yes| H[Review intent mapping]
  H --> I[Trigger remediation]
  I --> J[Validate QoS applied]
  J --> F
~~~

## Quickstart (WSL2)

Prerequisites:
- Docker Desktop with WSL2 integration
- WSL2 Ubuntu

1. Clone and enter the repo
~~~bash
git clone https://github.com/mukundmadhav054/smart_ai_network_monitor.git
cd smart_ai_network_monitor
~~~

2. Create environment file
~~~bash
cp .env.example .env
set -a
source .env
set +a
~~~

3. Bootstrap system deps (containerlab, iperf3, base packages)
~~~bash
chmod +x bootstrap/*.sh
./bootstrap/bootstrap_wsl.sh
~~~

4. Create Python environment with uv
~~~bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt -r requirements-dev.txt
~~~

5. Start the lab and observability stack
~~~bash
./bootstrap/start_lab.sh
~~~

Prometheus UI: http://localhost:9090
Grafana UI: http://localhost:3000

## Run the Simulator

~~~bash
source .venv/bin/activate
python simulator/telemetry_generator.py --serve-port 9108 --incident-every 60 --incident-duration 15
~~~

## Run the API

~~~bash
source .venv/bin/activate
uvicorn api.app:app --reload
~~~

## Trigger and Inspect Alerts

~~~bash
curl -s "http://localhost:8000/alerts?device=r2" | jq
~~~

## Manual Remediation

~~~bash
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/remediate_latency.yml -e "dry_run=true"
~~~

## API Remediation

~~~bash
if [[ -n "${REMEDIATE_API_TOKEN:-}" ]]; then
  curl -s -X POST http://localhost:8000/remediate \
    -H "Content-Type: application/json" \
    -H "X-API-Token: ${REMEDIATE_API_TOKEN}" \
    -d '{"symptom":"high_latency","dry_run":true,"canary":true}' | jq
else
  curl -s -X POST http://localhost:8000/remediate \
    -H "Content-Type: application/json" \
    -d '{"symptom":"high_latency","dry_run":true,"canary":true}' | jq
fi
~~~

`REMEDIATE_API_TOKEN` is optional for local development. If you set it in `.env`, the header is added automatically.

## Local Verification

~~~bash
ruff check .
pytest -q
ansible-lint ansible/playbooks/remediate_latency.yml
ansible-playbook --syntax-check -i ansible/inventory/hosts.yml ansible/playbooks/remediate_latency.yml
~~~

## Agents

- Overview: [AGENTS.md](AGENTS.md)
- Profiles: [.github/agents/README.md](.github/agents/README.md)

## Notes

- The lab uses FRR images only; swap in vendor images and adapters as needed.
- Keep secrets out of the repo and store them in .env or a secrets manager.
