"""Cache hit-rate surfacing tests.

The session cache hit rate (cache_read / prompt_tokens) must be visible
in the /cost report and in the /status panel, not only in log files.
"""

from run_agent import cache_hit_rate_line, render_cost_report


def _totals(cache_read=0, prompt=0):
    return {
        "input_tokens": max(0, prompt - cache_read),
        "output_tokens": 500,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": 0,
        "total_tokens": prompt + 500,
        "api_calls": 4,
    }


class TestCacheHitRateLine:
    def test_formats_pct(self):
        line = cache_hit_rate_line({"cache_read_tokens": 12400, "prompt_tokens": 19800})
        assert line is not None
        assert "63%" in line
        assert "12,400 / 19,800" in line

    def test_hidden_when_no_cache_reads(self):
        assert cache_hit_rate_line({"cache_read_tokens": 0, "prompt_tokens": 5000}) is None

    def test_hidden_when_no_prompts(self):
        assert cache_hit_rate_line({"cache_read_tokens": 100, "prompt_tokens": 0}) is None

    def test_no_division_error_on_zero(self):
        assert cache_hit_rate_line({}) is None

    def test_rounds_to_nearest_pct(self):
        line = cache_hit_rate_line({"cache_read_tokens": 1, "prompt_tokens": 3})
        assert "33%" in line


class TestCostReportIncludesRate:
    def test_report_contains_cache_hit_rate(self):
        lines = render_cost_report(
            model="m", totals={**_totals(cache_read=6200, prompt=9900), "prompt_tokens": 9900}
        )
        joined = "\n".join(lines)
        assert "Cache hit rate" in joined
        assert "62%" in joined or "63%" in joined

    def report_omits_rate_without_cache(self):
        lines = render_cost_report(model="m", totals=_totals(cache_read=0, prompt=4000))
        assert not any("Cache hit rate" in ln for ln in lines)
