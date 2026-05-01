from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np


@dataclass
class DetectionResult:
    is_anomaly: bool
    score: Optional[float]
    method: str
    message: str


class AnomalyDetector:
    def __init__(
        self,
        window: int = 10,
        z_threshold: float = 3.0,
        iforest_contamination: float = 0.1,
    ) -> None:
        self.window = window
        self.z_threshold = z_threshold
        self.iforest_contamination = iforest_contamination

    def detect(self, values: Iterable[float]) -> DetectionResult:
        series = np.array(list(values), dtype=float)
        if series.size == 0:
            return DetectionResult(False, None, "insufficient_data", "Need more samples")
        if not np.isfinite(series[-1]):
            return DetectionResult(False, None, "invalid_data", "Latest sample is not finite")
        if not np.all(np.isfinite(series)):
            series = series[np.isfinite(series)]
            if series.size == 0:
                return DetectionResult(False, None, "invalid_data", "No finite samples")
        if series.size < self.window + 1:
            return self._iforest_fallback(series)

        baseline = series[-(self.window + 1):-1]
        current = float(series[-1])
        mean = float(np.mean(baseline))
        std = float(np.std(baseline))

        if std == 0.0:
            return DetectionResult(False, 0.0, "zscore", "Zero variance in baseline")

        z_score = (current - mean) / std
        if z_score >= self.z_threshold:
            return DetectionResult(True, float(z_score), "zscore", "Z-score spike detected")
        if z_score <= -self.z_threshold:
            return DetectionResult(True, float(z_score), "zscore", "Z-score drop detected")

        return DetectionResult(False, float(z_score), "zscore", "No anomaly")

    def _iforest_fallback(self, series: np.ndarray) -> DetectionResult:
        if series.size < 5:
            return DetectionResult(False, None, "insufficient_data", "Need more samples")

        try:
            from sklearn.ensemble import IsolationForest
        except Exception:
            return DetectionResult(False, None, "insufficient_data", "IsolationForest unavailable")

        model = IsolationForest(
            contamination=self.iforest_contamination,
            random_state=7,
        )
        baseline = series[:-1]
        current = series[-1]
        model.fit(baseline.reshape(-1, 1))
        pred = model.predict(np.array([[current]]))[0]
        score = float(model.decision_function(np.array([[current]]))[0])
        if pred == -1:
            return DetectionResult(True, score, "isolation_forest", "Outlier detected")
        return DetectionResult(False, score, "isolation_forest", "No anomaly")
