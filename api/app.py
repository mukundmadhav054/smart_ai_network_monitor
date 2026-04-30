from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Protocol

import httpx
import yaml
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, make_asgi_app

from anomaly.detector import AnomalyDetector


REPO_ROOT = Path(__file__).resolve().parents[1]

PROM_BASE_URL = os.getenv("PROMETHEUS_BASE_URL", "http://localhost:9090")
LATENCY_METRIC = os.getenv("PROMETHEUS_LATENCY_METRIC", "network_latency_ms")
LOSS_METRIC = os.getenv("PROMETHEUS_LOSS_METRIC", "network_packet_loss_pct")
DEFAULT_DEVICE = os.getenv("SIMULATOR_DEVICE_ID", "r2")
LOOKBACK_MINUTES = int(os.getenv("ALERT_LOOKBACK_MINUTES", "5"))

ANSIBLE_INVENTORY = str((REPO_ROOT / "ansible/inventory/hosts.yml").resolve())
DEFAULT_PLAYBOOK = str((REPO_ROOT / "ansible/playbooks/remediate_latency.yml").resolve())
DEFAULT_CANARY_LIMIT = "r2"

INTENTS_PATH = REPO_ROOT / "intent/intents.yml"
ALLOWED_SYMPTOMS = {"high_latency", "packet_loss"}

ALERTS_TOTAL = Counter("samn_alerts_total", "Alerts emitted", ["metric", "device"])
REMEDIATIONS_TOTAL = Counter("samn_remediations_total", "Remediations invoked", ["status"])


class MetricsProvider(Protocol):
    def series(self, metric: str, device: str, lookback_minutes: int) -> List[float]:
        ...


@dataclass
class PrometheusMetricsProvider:
    base_url: str

    def series(self, metric: str, device: str, lookback_minutes: int) -> List[float]:
        end = time.time()
        start = end - (lookback_minutes * 60)
        step = max(5, int((lookback_minutes * 60) / 30))
        query = f'{metric}{{device="{device}"}}'

        url = f"{self.base_url}/api/v1/query_range"
        params = {"query": query, "start": start, "end": end, "step": step}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
        resp.raise_for_status()

        payload = resp.json()
        results = payload.get("data", {}).get("result", [])
        if not results:
            return []
        values = results[0].get("values", [])
        return [float(v[1]) for v in values]


class IntentStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._intents = self._load()

    def _load(self) -> dict:
        data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        return data or {}

    def get(self, symptom: str) -> dict | None:
        return self._intents.get(symptom)


def _resolve_playbook() -> str:
    playbook = Path(DEFAULT_PLAYBOOK)
    if not playbook.is_file():
        raise HTTPException(status_code=404, detail="Playbook not found")
    return str(playbook)


def _serialize_extra_vars(extra_vars: dict) -> str:
    safe_vars: dict[str, object] = {}
    for key, value in extra_vars.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(key)):
            raise HTTPException(status_code=400, detail="Invalid variable name")
        if not isinstance(value, (str, int, float, bool)):
            raise HTTPException(status_code=400, detail="Invalid variable type")
        safe_vars[str(key)] = value

    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="samn_vars_",
        suffix=".yml",
        delete=False,
    ) as handle:
        yaml.safe_dump(safe_vars, handle)
        return handle.name


def get_metrics_provider() -> MetricsProvider:
    return PrometheusMetricsProvider(base_url=PROM_BASE_URL)


def get_intent_store() -> IntentStore:
    return IntentStore(INTENTS_PATH)


app = FastAPI(title="Smart AI Network Monitor API", version="0.1.0")
app.mount("/metrics", make_asgi_app())

detector = AnomalyDetector()


class Alert(BaseModel):
    device: str
    metric: str
    current: float
    method: str
    score: float | None
    intent: str
    message: str


class RemediateRequest(BaseModel):
    symptom: str = Field(..., description="Intent key, e.g. high_latency or packet_loss")
    dry_run: bool = True
    canary: bool = True
    rollback: bool = False


class RemediateResult(BaseModel):
    command: List[str]
    return_code: int
    stdout: str
    stderr: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/alerts", response_model=List[Alert])
def alerts(
    device: str | None = None,
    metrics: MetricsProvider = Depends(get_metrics_provider),
    intents: IntentStore = Depends(get_intent_store),
) -> List[Alert]:
    device_id = device or DEFAULT_DEVICE
    latency_series = metrics.series(LATENCY_METRIC, device_id, LOOKBACK_MINUTES)
    loss_series = metrics.series(LOSS_METRIC, device_id, LOOKBACK_MINUTES)

    alerts_out: List[Alert] = []

    latency_result = detector.detect(latency_series)
    if latency_result.is_anomaly and latency_series:
        intent_key = "high_latency"
        intents.get(intent_key)
        ALERTS_TOTAL.labels(metric="latency", device=device_id).inc()
        alerts_out.append(
            Alert(
                device=device_id,
                metric=LATENCY_METRIC,
                current=float(latency_series[-1]),
                method=latency_result.method,
                score=latency_result.score,
                intent=intent_key,
                message=latency_result.message,
            )
        )

    loss_result = detector.detect(loss_series)
    if loss_result.is_anomaly and loss_series:
        intent_key = "packet_loss"
        intents.get(intent_key)
        ALERTS_TOTAL.labels(metric="loss", device=device_id).inc()
        alerts_out.append(
            Alert(
                device=device_id,
                metric=LOSS_METRIC,
                current=float(loss_series[-1]),
                method=loss_result.method,
                score=loss_result.score,
                intent=intent_key,
                message=loss_result.message,
            )
        )

    return alerts_out


def _build_ansible_command(
    playbook: str,
    extra_vars_path: str,
    dry_run: bool,
    canary: bool,
) -> List[str]:
    cmd = ["ansible-playbook", "-i", ANSIBLE_INVENTORY, playbook]
    if dry_run:
        cmd.append("--check")
    if canary:
        cmd += ["--limit", DEFAULT_CANARY_LIMIT]
    cmd += ["-e", f"@{extra_vars_path}"]
    return cmd


@app.post("/remediate", response_model=RemediateResult)
def remediate(
    request: RemediateRequest,
    intents: IntentStore = Depends(get_intent_store),
) -> RemediateResult:
    intent = intents.get(request.symptom)
    if not intent or request.symptom not in ALLOWED_SYMPTOMS:
        raise HTTPException(status_code=404, detail="Unknown intent")

    playbook = _resolve_playbook()
    extra_vars = intent.get("vars", {}).copy()
    extra_vars.update(
        {
            "dry_run": request.dry_run,
            "canary": request.canary,
            "rollback": request.rollback,
        }
    )

    extra_vars_path = _serialize_extra_vars(extra_vars)

    cmd = _build_ansible_command(
        playbook=playbook,
        extra_vars_path=extra_vars_path,
        dry_run=request.dry_run,
        canary=request.canary,
    )

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        REMEDIATIONS_TOTAL.labels(status="timeout").inc()
        raise HTTPException(status_code=504, detail="Remediation timed out") from exc
    finally:
        try:
            Path(extra_vars_path).unlink(missing_ok=True)
        except OSError:
            pass

    status = "ok" if result.returncode == 0 else "error"
    REMEDIATIONS_TOTAL.labels(status=status).inc()

    return RemediateResult(
        command=cmd,
        return_code=result.returncode,
        stdout=result.stdout[-4000:],
        stderr=result.stderr[-4000:],
    )

# TODO: Add authN/authZ and structured audit logging for production.
