"""Tests for anomaly detection (xavani_observability/anomaly.py, E03)."""

import pytest

from xavani_observability.anomaly import detect_anomalies, detect_spike


class TestDetectAnomalies:
    def test_flat_series_no_anomalies(self):
        assert detect_anomalies([5.0] * 30) == []

    def test_single_spike_detected(self):
        values = [10.0] * 20 + [1000.0] + [10.0] * 5
        anomalies = detect_anomalies(values)
        assert 20 in anomalies

    def test_gradual_trend_not_flagged(self):
        values = [float(i) for i in range(50)]
        assert detect_anomalies(values) == []

    def test_short_series_returns_nothing(self):
        assert detect_anomalies([1.0, 2.0, 3.0]) == []

    def test_empty_series(self):
        assert detect_anomalies([]) == []

    def test_negative_sigma_raises(self):
        with pytest.raises(ValueError):
            detect_anomalies([1.0, 2.0], sigma=-1)

    def test_high_sigma_still_flags_flat_baseline_spike(self):
        # Against a zero-variance baseline the z-score is infinite, so even
        # a very high sigma cannot hide the spike.
        values = [10.0] * 20 + [1000.0] + [10.0] * 5
        anomalies = detect_anomalies(values, sigma=100.0)
        assert 20 in anomalies

    def test_high_sigma_ignores_noisy_fluctuation(self):
        # With real variance, a small fluctuation stays under a high sigma.
        import random
        random.seed(42)
        values = [100 + random.uniform(-1, 1) for _ in range(30)] + [101.0]
        assert detect_anomalies(values, sigma=10.0) == []

    def test_low_sigma_flags_more(self):
        values = [10.0] * 20 + [15.0] + [10.0] * 5
        anomalies = detect_anomalies(values, sigma=1.0)
        assert anomalies  # the 15 deviates >1 sigma from the flat 10s


class TestDetectSpike:
    def test_returns_most_recent_anomaly(self):
        values = [10.0] * 20 + [1000.0, 10.0, 2000.0]
        assert detect_spike(values) == 22

    def test_none_without_anomaly(self):
        assert detect_spike([5.0] * 30) is None
