from fastapi.testclient import TestClient
import api.app as api_app

from api.app import INTENTS_PATH, IntentStore, app, get_metrics_provider
from simulator.telemetry_generator import TelemetryGenerator


class BufferMetricsProvider:
    def __init__(self, generator: TelemetryGenerator) -> None:
        self.generator = generator

    def series(self, metric: str, device: str, lookback_minutes: int):
        return self.generator.get_series(metric, device, lookback_minutes * 60)


def test_alerts_from_simulator() -> None:
    generator = TelemetryGenerator(device="r2", seed=7)
    for _ in range(15):
        generator.step(incident=False)
    generator.step(incident=True)

    provider = BufferMetricsProvider(generator)
    app.dependency_overrides[get_metrics_provider] = lambda: provider

    client = TestClient(app)
    resp = client.get("/alerts?device=r2")
    assert resp.status_code == 200
    alerts = resp.json()
    assert any(alert["intent"] == "high_latency" for alert in alerts)
    assert any(alert["severity"] == "warning" for alert in alerts)

    app.dependency_overrides.clear()


def test_intent_store_matches_regex_aliases() -> None:
    store = IntentStore(INTENTS_PATH)

    match = store.match("latency spike")

    assert match is not None
    assert match.key == "high_latency"
    assert match.severity == "warning"


def test_intent_store_matches_packet_loss_severity() -> None:
    store = IntentStore(INTENTS_PATH)

    match = store.match("loss-degradation")

    assert match is not None
    assert match.key == "packet_loss"
    assert match.severity == "critical"


def test_remediate_accepts_regex_alias(monkeypatch) -> None:
    captured = {}

    def fake_run(cmd, check, capture_output, text, timeout):
        captured["cmd"] = cmd
        captured["check"] = check
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        return api_app.subprocess.CompletedProcess(cmd, 0, "ok", "")

    monkeypatch.setattr(api_app.subprocess, "run", fake_run)

    client = TestClient(app)
    resp = client.post(
        "/remediate",
        json={"symptom": "latency spike", "dry_run": True, "canary": True},
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["return_code"] == 0
    assert "--check" in captured["cmd"]
    assert "--limit" in captured["cmd"]
