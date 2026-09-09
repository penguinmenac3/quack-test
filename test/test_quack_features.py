"""
Tests for quack-test's own behavior (async support, Samples, stop_early,
parallel, result coercion, error reporting, markers).

These tests call the decorated functions directly, so no LLM credentials are
required. End-to-end collection behavior is verified via pytester.
"""

import asyncio
import time
from dataclasses import dataclass

import pytest

from quack_test import Samples, nondeterministic_test

pytest_plugins = ["pytester"]


def test_async_test_runs_natively():
    calls = []

    @nondeterministic_test(n=3, threshold=0.8)
    async def check():
        await asyncio.sleep(0)
        calls.append(1)
        return True

    check()
    assert len(calls) == 3


def test_async_test_failure_counts():
    @nondeterministic_test(n=2, threshold=0.9)
    async def check():
        return False

    with pytest.raises(AssertionError, match="Test failed to meet success threshold"):
        check()


def test_samples_indexed_per_run():
    received = []

    @nondeterministic_test(threshold=0.0)
    def check(value):
        received.append(value)

    check(Samples([10, 20, 30]))
    assert received == [10, 20, 30]


def test_plain_lists_passed_through_unchanged():
    received = []

    @nondeterministic_test(n=2, threshold=0.0)
    def check(history):
        assert history == ["a", "b"]
        received.append(history)

    check(["a", "b"])
    assert received == [["a", "b"], ["a", "b"]]


def test_first_object_arg_not_misdetected_as_self():
    @dataclass
    class Payload:
        values: list

    received = []

    @nondeterministic_test(n=2, threshold=0.8)
    def check(payload):
        received.append(payload)
        return True

    payload = Payload(values=[1, 2])
    check(payload)
    assert received == [payload, payload]


def test_class_method_receives_self():
    class Helper:
        def __init__(self):
            self.calls = 0

        @nondeterministic_test(n=2, threshold=0.5)
        def check(self):
            self.calls += 1
            return True

    helper = Helper()
    helper.check()
    assert helper.calls == 2


def test_stop_early_guaranteed_pass():
    calls = []

    @nondeterministic_test(n=10, threshold=0.6, stop_early=True)
    def check():
        calls.append(1)
        return 1.0

    check()
    # After 6 perfect runs: mean is >= 0.6 even if the rest score 0.
    assert len(calls) == 6


def test_stop_early_guaranteed_failure():
    calls = []

    @nondeterministic_test(n=10, threshold=0.6, stop_early=True)
    def check():
        calls.append(1)
        return 0.0

    with pytest.raises(AssertionError, match="stopped early after 5/10 runs"):
        check()
    # After 5 zero runs: mean stays below 0.6 even if the rest score 1.
    assert len(calls) == 5


def test_stop_early_should_fail():
    calls = []

    @nondeterministic_test(n=10, threshold=0.5, should_fail=True, stop_early=True)
    def check():
        calls.append(1)
        return 0.0

    check()
    # After 6 zero runs: mean is < 0.5 even if the rest score 1.
    assert len(calls) == 6


def test_parallel_sync_runs_all_concurrently():
    runs = []

    @nondeterministic_test(n=5, threshold=1.0, parallel=True)
    def check():
        runs.append(1)
        time.sleep(0.2)
        return True

    start = time.monotonic()
    check()
    elapsed = time.monotonic() - start
    assert len(runs) == 5
    # Sequential execution would take ~1.0s.
    assert elapsed < 0.8


def test_parallel_async_runs_all_concurrently():
    runs = []

    @nondeterministic_test(n=5, threshold=1.0, parallel=True)
    async def check():
        runs.append(1)
        await asyncio.sleep(0.2)
        return True

    start = time.monotonic()
    check()
    elapsed = time.monotonic() - start
    assert len(runs) == 5
    # Sequential execution would take ~1.0s.
    assert elapsed < 0.8


def test_parallel_and_stop_early_are_mutually_exclusive():
    with pytest.raises(ValueError, match="mutually exclusive"):
        nondeterministic_test(parallel=True, stop_early=True)


def test_bool_results_are_coerced():
    @nondeterministic_test(n=2, threshold=1.0)
    def returns_true():
        return True

    returns_true()

    @nondeterministic_test(n=2, threshold=0.5)
    def returns_false():
        return False

    with pytest.raises(AssertionError):
        returns_false()


def test_int_results_are_coerced():
    @nondeterministic_test(n=2, threshold=1.0)
    def returns_one():
        return 1

    returns_one()

    @nondeterministic_test(n=2, threshold=0.5)
    def returns_zero():
        return 0

    with pytest.raises(AssertionError):
        returns_zero()


def test_exception_message_is_reported():
    @nondeterministic_test(n=2, threshold=0.9)
    def check():
        raise ValueError("kaboom")

    with pytest.raises(AssertionError, match="ValueError: kaboom"):
        check()


def test_score_exactly_at_threshold_counts_as_success():
    scores = iter([0.6, 0.0])

    @nondeterministic_test(n=2, threshold=0.6)
    def check():
        return next(scores)

    with pytest.raises(AssertionError, match=r"\(1/2\)"):
        check()


def test_async_runs_share_one_event_loop():
    loops = []

    @nondeterministic_test(n=3, threshold=0.5)
    async def check():
        loops.append(asyncio.get_running_loop())
        return True

    check()
    assert len(set(loops)) == 1
    assert not loops[0].is_closed()


def test_async_tests_share_event_loop_across_tests():
    loops = []

    @nondeterministic_test(n=2, threshold=0.5)
    async def check_a():
        loops.append(asyncio.get_running_loop())
        return True

    @nondeterministic_test(n=2, threshold=0.5)
    async def check_b():
        loops.append(asyncio.get_running_loop())
        return True

    check_a()
    check_b()
    assert len(set(loops)) == 1


def test_failure_message_includes_run_scores():
    scores = iter([1.0, 0.0, 1.0, 1.0, 1.0])

    @nondeterministic_test(n=5, threshold=0.9)
    def check():
        return next(scores)

    with pytest.raises(
        AssertionError, match=r"run scores: \[1\.00, 0\.00, 1\.00, 1\.00, 1\.00\]"
    ):
        check()


def test_nondeterministic_marker_applied():
    @nondeterministic_test(n=1, threshold=0.0)
    def check():
        pass

    marks = getattr(check, "pytestmark", [])
    assert any(m.name == "nondeterministic" for m in marks)


def test_async_fixture_and_test_end_to_end(pytester):
    pytester.makepyfile(
        """
        import asyncio
        from quack_test import nondeterministic_fixture, nondeterministic_test

        fixture_loops = []
        test_loops = []

        @nondeterministic_fixture(n=3)
        async def sample():
            await asyncio.sleep(0)
            fixture_loops.append(asyncio.get_running_loop())
            return "3 apples."

        @nondeterministic_test(threshold=0.8)
        async def test_async(sample):
            test_loops.append(asyncio.get_running_loop())
            assert "apples" in sample

        def test_shared_loop():
            assert len(set(fixture_loops) | set(test_loops)) == 1
        """
    )
    result = pytester.runpytest_inprocess()
    result.assert_outcomes(passed=2)


def test_marker_filtering_end_to_end(pytester):
    pytester.makepyfile(
        """
        from quack_test import nondeterministic_test

        @nondeterministic_test(n=2, threshold=0.5)
        def test_quack():
            return True

        def test_plain():
            assert True
        """
    )
    result = pytester.runpytest_inprocess("-m", "not nondeterministic")
    result.assert_outcomes(passed=1, deselected=1)
    result = pytester.runpytest_inprocess("-m", "nondeterministic")
    result.assert_outcomes(passed=1, deselected=1)
