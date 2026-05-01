# PLAN

## Intent
Provide a minimal, reproducible MVP for Smart AI Network Monitor that runs on WSL2 and demonstrates the full pipeline:
telemetry ingestion -> anomaly detection -> intent mapping -> safe Ansible remediation.

## Workflow
1. Bootstrap the environment (WSL2, containerlab, Python, tooling).
2. Start observability stack (Prometheus + Grafana).
3. Launch the lab topology (FRR routers + host1).
4. Run telemetry simulator to generate metrics.
5. Run the API to detect anomalies and map intents.
6. Trigger remediation via API or direct Ansible playbook.
7. Validate with tests and CI.

## Milestones
- M1: Lab and observability stack online.
- M2: Ansible remediation with dry_run/canary/rollback.
- M3: Simulator + anomaly detector + API.
- M4: CI + docs + templates.

## Completed This Iteration
- Prometheus targets resolve on Linux with a host alias.
- Grafana dashboard includes latency, loss, and alert panels.
- Bootstrap validates a Prometheus query after startup.
- /remediate supports an optional API token and Prometheus responses are validated.
- Detector handles invalid inputs and negative anomalies; fallback avoids current sample.
- Ansible canary gating, rollback safety checks, and QoS validation are in place.
- Quickstart documents .env loading and CI runs an API health smoke test.

## Next Step Backlog
- Add containerlab node exporters or native telemetry exporters for in-lab metrics.
- Add structured audit logging for remediation requests and outcomes.
- Expand Grafana dashboard with anomaly score and remediation status panels.

## Key Paths
- Topology: containerlab/topology.yml
- Observability: infrastructure/docker-compose.yml, infrastructure/prometheus/prometheus.yml
- Simulator: simulator/telemetry_generator.py
- Detector: anomaly/detector.py
- API: api/app.py
- Intent store: intent/intents.yml
- Remediation: ansible/playbooks/remediate_latency.yml
- CI: .github/workflows/ci.yml

## Quality Gates
- ruff check .
- pytest -q
- ansible-lint ansible/playbooks/remediate_latency.yml
- ansible-playbook --syntax-check -i ansible/inventory/hosts.yml ansible/playbooks/remediate_latency.yml

## Notes
- Keep secrets in .env or external secret stores.
- Use FRR for the MVP; add vendor adapters as separate roles/templates.
