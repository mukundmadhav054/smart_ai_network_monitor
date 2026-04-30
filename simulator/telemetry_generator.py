#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List

from prometheus_client import Gauge, start_http_server


LATENCY_GAUGE = Gauge(
    "network_latency_ms",
    "Synthetic latency in milliseconds",
    ["device", "interface"],
)
LOSS_GAUGE = Gauge(
    "network_packet_loss_pct",
    "Synthetic packet loss percent",
    ["device", "interface"],
)


@dataclass
class TelemetrySample:
    timestamp: float
    device: str
    interface: str
    latency_ms: float
    loss_pct: float


class TelemetryGenerator:
    def __init__(
        self,
        device: str,
        interface: str = "eth2",
        history_size: int = 600,
        seed: int | None = None,
        baseline_latency_ms: float = 40.0,
        latency_jitter_ms: float = 4.0,
        baseline_loss_pct: float = 0.2,
        loss_jitter_pct: float = 0.1,
        incident_latency_ms: float = 120.0,
        incident_loss_pct: float = 3.0,
    ) -> None:
        self.device = device
        self.interface = interface
        self.baseline_latency_ms = baseline_latency_ms
        self.latency_jitter_ms = latency_jitter_ms
        self.baseline_loss_pct = baseline_loss_pct
        self.loss_jitter_pct = loss_jitter_pct
        self.incident_latency_ms = incident_latency_ms
        self.incident_loss_pct = incident_loss_pct
        self.rng = random.Random(seed)
        self.samples: Deque[TelemetrySample] = deque(maxlen=history_size)

    def _base_latency(self) -> float:
        return max(0.1, self.rng.normalvariate(self.baseline_latency_ms, self.latency_jitter_ms))

    def _base_loss(self) -> float:
        return max(0.0, self.rng.normalvariate(self.baseline_loss_pct, self.loss_jitter_pct))

    def step(self, incident: bool = False) -> TelemetrySample:
        latency = self._base_latency()
        loss = self._base_loss()

        if incident:
            latency += self.incident_latency_ms
            loss += self.incident_loss_pct

        LATENCY_GAUGE.labels(device=self.device, interface=self.interface).set(latency)
        LOSS_GAUGE.labels(device=self.device, interface=self.interface).set(loss)

        sample = TelemetrySample(
            timestamp=time.time(),
            device=self.device,
            interface=self.interface,
            latency_ms=latency,
            loss_pct=loss,
        )
        self.samples.append(sample)
        return sample

    def get_series(self, metric: str, device: str, lookback_seconds: int) -> List[float]:
        cutoff = time.time() - lookback_seconds
        values: List[float] = []
        for sample in self.samples:
            if sample.timestamp < cutoff:
                continue
            if sample.device != device:
                continue
            if metric == "network_latency_ms":
                values.append(sample.latency_ms)
            elif metric == "network_packet_loss_pct":
                values.append(sample.loss_pct)
            else:
                raise ValueError(f"Unknown metric: {metric}")
        return values


def _incident_active(now: float, incident: bool, incident_every: int, incident_duration: int) -> bool:
    if incident:
        return True
    if incident_every <= 0 or incident_duration <= 0:
        return False
    return int(now) % incident_every < incident_duration


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic telemetry generator for Prometheus.")
    parser.add_argument("--device", default="r2", help="Device label value")
    parser.add_argument("--interface", default="eth2", help="Interface label value")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between samples")
    parser.add_argument("--serve-port", type=int, default=9108, help="Prometheus metrics port")
    parser.add_argument("--incident", action="store_true", help="Force incident mode")
    parser.add_argument("--incident-every", type=int, default=0, help="Incident every N seconds")
    parser.add_argument("--incident-duration", type=int, default=15, help="Incident duration in seconds")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for repeatability")
    args = parser.parse_args()

    generator = TelemetryGenerator(device=args.device, interface=args.interface, seed=args.seed)

    start_http_server(args.serve_port)
    print(f"Serving Prometheus metrics on :{args.serve_port}")

    while True:
        now = time.time()
        incident_on = _incident_active(now, args.incident, args.incident_every, args.incident_duration)
        generator.step(incident=incident_on)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
