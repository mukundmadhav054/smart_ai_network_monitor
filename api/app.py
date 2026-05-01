from __future__ import annotations

import logging
import os
import re
import secrets
import subprocess
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import List, Protocol

import httpx
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from prometheus_client import Counter, make_asgi_app

from anomaly.detector import AnomalyDetector


REPO_ROOT = Path(__file__).resolve().parents[1]

PROM_BASE_URL = os.getenv("PROMETHEUS_BASE_URL", "http://localhost:9090")
LATENCY_METRIC = os.getenv("PROMETHEUS_LATENCY_METRIC", "network_latency_ms")
LOSS_METRIC = os.getenv("PROMETHEUS_LOSS_METRIC", "network_packet_loss_pct")
DEFAULT_DEVICE = os.getenv("SIMULATOR_DEVICE_ID", "r2")
LOOKBACK_MINUTES = int(os.getenv("ALERT_LOOKBACK_MINUTES", "5"))
REMEDIATE_API_TOKEN = os.getenv("REMEDIATE_API_TOKEN", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("ENV", "dev")).lower()

ANSIBLE_INVENTORY = str((REPO_ROOT / "ansible/inventory/hosts.yml").resolve())
DEFAULT_PLAYBOOK = str((REPO_ROOT / "ansible/playbooks/remediate_latency.yml").resolve())
DEFAULT_CANARY_LIMIT = "r2"

INTENTS_PATH = REPO_ROOT / "intent/intents.yml"

ALERTS_TOTAL = Counter("samn_alerts_total", "Alerts emitted", ["metric", "device"])
REMEDIATIONS_TOTAL = Counter("samn_remediations_total", "Remediations invoked", ["status"])

LOG = logging.getLogger("samn_api")
PROM_CLIENT = httpx.Client(timeout=10.0)
DEVICE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class MetricsProvider(Protocol):
    def series(self, metric: str, device: str, lookback_minutes: int) -> List[float]:
        ...


@dataclass
class PrometheusMetricsProvider:
    base_url: str

    def series(self, metric: str, device: str, lookback_minutes: int) -> List[float]:
        if not DEVICE_PATTERN.fullmatch(device):
            raise HTTPException(status_code=400, detail="Invalid device identifier")
        end = time.time()
        start = end - (lookback_minutes * 60)
        step = max(5, int((lookback_minutes * 60) / 30))
        query = f'avg by (device) ({metric}{{device="{device}"}})'

        url = f"{self.base_url}/api/v1/query_range"
        params = {"query": query, "start": start, "end": end, "step": step}
        resp = PROM_CLIENT.get(url, params=params)
        resp.raise_for_status()

        payload = resp.json()
        if payload.get("status") != "success":
            raise HTTPException(status_code=502, detail="Prometheus query failed")
        results = payload.get("data", {}).get("result", [])
        if len(results) > 1:
            raise HTTPException(status_code=502, detail="Prometheus query returned multiple series")
        if not results:
            return []
        values = results[0].get("values", [])
        return [float(v[1]) for v in values]


@dataclass(frozen=True)
class IntentMatch:
    key: str
    definition: dict

    @property
    def severity(self) -> str:
        return str(self.definition.get("severity", "warning"))


class IntentStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._intents = self._load()

    def _load(self) -> dict:
        data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        return data or {}

    def get(self, symptom: str) -> dict | None:
        return self._intents.get(symptom)

    def match(self, symptom: str) -> IntentMatch | None:
        exact = self.get(symptom)
        if exact is not None:
            return IntentMatch(key=symptom, definition=exact)

        for key, definition in self._intents.items():
            for pattern in definition.get("match", []):
                try:
                    if re.fullmatch(str(pattern), symptom, flags=re.IGNORECASE):
                        return IntentMatch(key=str(key), definition=definition)
                except re.error as exc:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Invalid intent match pattern for {key}",
                    ) from exc
        return None


def _resolve_playbook(playbook_path: str | None = None) -> str:
    configured = playbook_path or DEFAULT_PLAYBOOK
    playbook = Path(configured)
    if not playbook.is_absolute():
        playbook = REPO_ROOT / playbook
    playbook = playbook.resolve()

    try:
        playbook.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Playbook path must stay within repository") from exc

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


def require_remediate_token(
    x_api_token: str | None = Header(default=None, alias="X-API-Token"),
) -> None:
    if not REMEDIATE_API_TOKEN:
        return
    if not x_api_token or not secrets.compare_digest(x_api_token, REMEDIATE_API_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not REMEDIATE_API_TOKEN:
        LOG.warning(
            "REMEDIATE_API_TOKEN is not set; /remediate is unauthenticated in %s mode",
            ENVIRONMENT,
        )
    yield
    PROM_CLIENT.close()


app = FastAPI(title="Smart AI Network Monitor API", version="0.1.0", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())

detector = AnomalyDetector()


class Alert(BaseModel):
    device: str
    metric: str
    current: float
    method: str
    score: float | None
    intent: str
    severity: str
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
        intent_match = intents.match(intent_key) or IntentMatch(intent_key, {})
        ALERTS_TOTAL.labels(metric="latency", device=device_id).inc()
        alerts_out.append(
            Alert(
                device=device_id,
                metric=LATENCY_METRIC,
                current=float(latency_series[-1]),
                method=latency_result.method,
                score=latency_result.score,
                intent=intent_key,
                severity=intent_match.severity,
                message=latency_result.message,
            )
        )

    loss_result = detector.detect(loss_series)
    if loss_result.is_anomaly and loss_series:
        intent_key = "packet_loss"
        intent_match = intents.match(intent_key) or IntentMatch(intent_key, {})
        ALERTS_TOTAL.labels(metric="loss", device=device_id).inc()
        alerts_out.append(
            Alert(
                device=device_id,
                metric=LOSS_METRIC,
                current=float(loss_series[-1]),
                method=loss_result.method,
                score=loss_result.score,
                intent=intent_key,
                severity=intent_match.severity,
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
    _token_ok: None = Depends(require_remediate_token),
) -> RemediateResult:
    LOG.info("Remediation requested", extra={"intent": request.symptom, "dry_run": request.dry_run})
    intent_match = intents.match(request.symptom)
    if not intent_match:
        raise HTTPException(status_code=404, detail="Unknown intent")
    intent = intent_match.definition

    playbook = _resolve_playbook(intent.get("playbook"))
    extra_vars = intent.get("vars", {}).copy()
    extra_vars.update(
        {
            "intent": intent_match.key,
            "severity": intent_match.severity,
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
