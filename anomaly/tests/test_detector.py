from anomaly.detector import AnomalyDetector


def test_zscore_detects_spike() -> None:
    detector = AnomalyDetector(window=10, z_threshold=3.0)
    values = [40.0 + (i % 3) for i in range(20)] + [200.0]
    result = detector.detect(values)
    assert result.is_anomaly
    assert result.method == "zscore"


def test_zscore_no_anomaly() -> None:
    detector = AnomalyDetector(window=10, z_threshold=3.0)
    values = [40.0 + (i % 3) for i in range(30)]
    result = detector.detect(values)
    assert not result.is_anomaly


def test_zscore_detects_drop() -> None:
    detector = AnomalyDetector(window=10, z_threshold=3.0)
    values = [40.0 + (i % 3) for i in range(20)] + [5.0]
    result = detector.detect(values)
    assert result.is_anomaly
    assert result.method == "zscore"


def test_invalid_latest_sample() -> None:
    detector = AnomalyDetector(window=10, z_threshold=3.0)
    values = [40.0 + (i % 3) for i in range(20)] + [float("nan")]
    result = detector.detect(values)
    assert not result.is_anomaly
    assert result.method == "invalid_data"


def test_iforest_fallback_short_series() -> None:
    detector = AnomalyDetector(window=10, z_threshold=3.0)
    values = [1.0, 1.1, 0.9, 1.05]
    result = detector.detect(values)
    assert result.method == "insufficient_data"
