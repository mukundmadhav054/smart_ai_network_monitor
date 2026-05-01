# Changelog
All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]
### Added
- Intent regex aliases and severity metadata for alert and remediation mapping.
- Containerlab topology baseline with FRR routers and host1.
- Prometheus and Grafana docker-compose stack with Grafana provisioning.
- Prometheus scrape targets for simulator and API metrics.
- Grafana dashboard panels for latency, loss, and alert totals.
- Optional remediation API token gate via X-API-Token header.
- CI API health smoke test and basic /health unit test.
- QoS validation step after apply in the remediation playbook.
- Workflow guide with flowchart and end-to-end steps.
- Dashboard panels for remediation totals and alerts by metric.

### Changed
- Prometheus queries aggregate by device and validate response status.
- Inventory defaults now prefer env-driven non-root SSH settings.
- Detection treats negative spikes as anomalies and rejects invalid samples.

### Fixed
- Prometheus scrape configuration indentation and label placement.
- Prometheus host alias for Linux docker compose networking.
- Safer rollback when backup files are missing.
- IsolationForest fallback now avoids training on the current sample.
- README remediation example now handles optional API tokens explicitly.
- Prometheus device labels are validated before query construction.
- Remediation playbook dry-run failures are logged and re-raised.
- Containerlab topology and docker-compose YAML use spaces for indentation.

## [0.1.0] - 2026-04-30
### Added
- containerlab topology with FRR routers and host1 traffic generator.
- Prometheus and Grafana observability stack.
- Telemetry simulator with Prometheus metrics endpoint.
- Rolling z-score anomaly detector with IsolationForest fallback.
- Intent mapping store and remediation playbook with dry_run/canary/rollback.
- FastAPI service exposing /health, /alerts, and /remediate endpoints.
- Unit and integration tests with pytest.
- CI pipeline for lint, tests, and ansible-lint.
