# Changelog
All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]
- Pending items and future improvements.

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
