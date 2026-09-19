"""Wilson interval and percentile math (spec B4.2)."""
import pytest

from core.scoring.metrics import percentile, wilson


class TestWilson:
    def test_empty(self):
        assert wilson(0, 0) == (0.0, 0.0)

    def test_zero_successes_n10(self):
        lo, hi = wilson(0, 10)
        assert lo == 0.0
        assert hi == pytest.approx(0.2776, abs=1e-3)

    def test_all_successes_n10(self):
        lo, hi = wilson(10, 10)
        assert lo == pytest.approx(0.7224, abs=1e-3)
        assert hi == pytest.approx(1.0)

    def test_half_successes(self):
        lo, hi = wilson(5, 10)
        assert lo == pytest.approx(0.2366, abs=1e-3)
        assert hi == pytest.approx(0.7634, abs=1e-3)

    def test_interval_narrows_with_n(self):
        narrow = wilson(50, 100)[1] - wilson(50, 100)[0]
        wide = wilson(5, 10)[1] - wilson(5, 10)[0]
        assert narrow < wide


class TestPercentile:
    def test_p50(self):
        assert percentile([1, 2, 3, 4, 5], 50) == 3

    def test_p95_interpolates(self):
        vs = list(range(1, 101))
        assert percentile(vs, 95) == pytest.approx(95.05, abs=0.01)

    def test_empty(self):
        assert percentile([], 95) == 0.0
