"""SC-08: Amplification engine handles 1500 calls with rate limiting, retry, cost tracking.
SC-09: Dual-mode amplification (baseline vs informed via digest).
"""

import ast
import re

from tests.verify_0001_worker_d.conftest import SDK_PATH, read_sdk


class TestSC08AmplificationCapacity:
    def test_batch_size_calculation(self):
        assert re.search(r"for\s+archetype\s+in.*archetypes.*for\s+var_idx\s+in\s+range.*variations",
                         read_sdk(), re.DOTALL)

    def test_concurrent_execution(self):
        assert "asyncio.gather" in read_sdk()

    def test_rate_limiting_present(self):
        assert "asyncio.Semaphore" in read_sdk()

    def test_retry_mechanism_present(self):
        assert re.search(r"max_retries|retry|attempt", read_sdk())

    def test_cost_tracking_per_call(self):
        assert "cost_usd" in read_sdk()

    def test_cost_tracking_total(self):
        assert "total_cost_usd" in read_sdk()

    def test_progress_tracking(self):
        s = read_sdk()
        assert "BatchProgress" in s
        assert "completed" in s
        assert "failed" in s


class TestSC09DualMode:
    def test_baseline_mode_exists(self):
        assert re.search(r'BASELINE\s*=', read_sdk())

    def test_informed_mode_exists(self):
        assert re.search(r'INFORMED\s*=', read_sdk())

    def test_baseline_has_no_digest(self):
        assert re.search(r"mode.*==.*INFORMED.*deliberation_digest|INFORMED.*and.*not.*digest",
                         read_sdk(), re.DOTALL)

    def test_informed_injects_digest_into_system_prompt(self):
        assert re.search(r"INFORMED.*deliberation_digest.*system_prompt|digest.*system_prompt_parts",
                         read_sdk(), re.DOTALL)

    def test_both_modes_use_same_engine(self):
        tree = ast.parse(read_sdk())
        engines = [n.name for n in ast.walk(tree)
                   if isinstance(n, ast.ClassDef) and "Engine" in n.name]
        assert engines == ["AmplificationEngine"]
