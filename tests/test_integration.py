from fastapi.testclient import TestClient

from api.app import app, get_metrics_provider
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

    app.dependency_overrides.clear()
