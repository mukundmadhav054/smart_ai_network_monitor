# Workflow Guide

This guide walks through the full MVP workflow with a visual flowchart and a simple checklist.

## Workflow Flowchart

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

## Step-by-step

1. Load environment variables
~~~bash
cp .env.example .env
set -a
source .env
set +a
~~~

2. Bootstrap dependencies
~~~bash
./bootstrap/bootstrap_wsl.sh
~~~

3. Start lab stack
~~~bash
./bootstrap/start_lab.sh
~~~

4. Run telemetry simulator
~~~bash
source .venv/bin/activate
python simulator/telemetry_generator.py --serve-port 9108 --incident-every 60 --incident-duration 15
~~~

5. Run the API
~~~bash
source .venv/bin/activate
uvicorn api.app:app --reload
~~~

6. Check alert output
~~~bash
curl -s "http://localhost:8000/alerts?device=r2" | jq
~~~

7. Trigger remediation (optional)
~~~bash
curl -s -X POST http://localhost:8000/remediate \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $REMEDIATE_API_TOKEN" \
  -d '{"symptom":"high_latency","dry_run":true,"canary":true}' | jq
~~~

## Visual Dashboards

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Troubleshooting

- If Prometheus has no data, confirm the simulator is running on port 9108.
- If Grafana panels are empty, confirm the Prometheus datasource is healthy.
- If remediation is unauthorized, set `REMEDIATE_API_TOKEN` in `.env` and pass it in the request header.
