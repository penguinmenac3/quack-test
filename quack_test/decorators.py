"""
Decorators for handling nondeterministic tests and fixtures.
"""

import asyncio
import functools
import inspect
import numbers
import pytest
from typing import Callable, Any, Literal

from quack_test._runtime import run_coroutine
from quack_test.plugin import record_result

# Fixture scopes ("function" ... "session"); defined locally instead of
# importing the private _pytest.scope module (renamed in pytest 9.1).
ScopeName = Literal["session", "package", "module", "class", "function"]


class Samples(list):
    """
    Marks list arguments of a nondeterministic test as per-run sample data.

    Fixtures created with ``nondeterministic_fixture`` return ``Samples``
    automatically, so the i-th run receives the i-th sample. Plain lists
    (e.g. chat histories) are passed to the test unchanged instead of being
    indexed per run. Wrap your own data in ``Samples(...)`` to opt into
    per-run indexing:

    Example:
        @nondeterministic_test()
        def test_greeting(output):
            return judge(output, criterion="Contains 'hello'")

        test_greeting(Samples(["hi there", "good morning"]))
    """


def _expects_self(func: Callable) -> bool:
    """Detect at decoration time whether func is a method expecting self/cls."""
    qualname: str = getattr(func, "__qualname__", "")
    parts = qualname.split(".")
    if len(parts) < 2 or parts[-2] == "<locals>":
        return False
    try:
        params = list(inspect.signature(func).parameters)
    except (TypeError, ValueError):
        return True
    return bool(params) and params[0] in ("self", "cls")


def _to_score(result: Any) -> tuple[float, str]:
    """Normalize a test return value into a (score, reason) pair."""
    if result is None:
        return 1.0, ""
    if isinstance(result, numbers.Real):
        return float(result), ""
    if isinstance(result, str):
        return 1.0, result
    score, reason = result
    return float(score), str(reason)


def _decision_final(
    scores: list[float], n_runs: int, threshold: float, should_fail: bool
) -> bool:
    """Check whether the outcome is already decided, assuming scores in [0, 1]."""
    executed = len(scores)
    if executed >= n_runs:
        return True
    remaining = n_runs - executed
    total = sum(scores)
    min_final = total / n_runs  # remaining runs all score 0
    max_final = (total + remaining) / n_runs  # remaining runs all score 1
    if should_fail:
        # Pass means final mean < threshold.
        return max_final < threshold or min_final >= threshold
    # Pass means final mean >= threshold.
    return min_final >= threshold or max_final < threshold


def nondeterministic_fixture(
    n: int = 5, scope: ScopeName = "module", parallel: bool = False
):
    """
    Decorator for fixtures that should be executed multiple times.

    The fixture function will be executed `n` times, and all results
    will be collected into a ``Samples`` list. This list is then passed to tests
    that depend on this fixture, where each run receives the i-th sample.

    Args:
        n: Number of times to execute the fixture (default: 5)
        parallel: If True, generate the samples concurrently instead of
            sequentially (default: False). Async fixture functions are awaited
            concurrently, sync functions run in a thread pool.

    Example:
        @nondeterministic_fixture(n=10)
        def random_data():
            return random.randint(1, 100)

        # The test will receive the samples one element at a time, per run
        def test_values(random_data):
            assert 1 <= random_data <= 100
    """

    def decorator(func: Callable) -> Callable:
        if parallel:

            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Samples:
                async def _collect():
                    if asyncio.iscoroutinefunction(func):
                        return await asyncio.gather(
                            *[func(*args, **kwargs) for _ in range(n)]
                        )
                    loop = asyncio.get_running_loop()
                    return await asyncio.gather(
                        *[
                            loop.run_in_executor(
                                None, functools.partial(func, *args, **kwargs)
                            )
                            for _ in range(n)
                        ]
                    )

                return Samples(run_coroutine(_collect()))

        elif asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Samples:
                async def _collect():
                    return Samples([await func(*args, **kwargs) for _ in range(n)])

                return run_coroutine(_collect())

        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Samples:
                return Samples([func(*args, **kwargs) for _ in range(n)])

        # Mark this as a pytest fixture
        return pytest.fixture(wrapper, scope=scope)

    return decorator


def nondeterministic_test(
    threshold: float = 0.8,
    n: int = -1,
    should_fail: bool = False,
    parallel: bool = False,
    stop_early: bool = False,
):
    """
    Decorator for tests that should be executed multiple times with a success threshold.

    The test function will be executed multiple times (determined by the length of
    the ``Samples`` fixture data if available, or by ``n``). The test must return
    a score which will be averaged. If the average score is at least the given
    threshold, you pass. Tests are automatically marked with the ``nondeterministic``
    marker, so they can be deselected via ``pytest -m "not nondeterministic"``.

    Async test and fixture functions (``async def``) are supported natively and
    awaited on a single event loop shared across the whole test session, so
    loop-bound resources (e.g. singleton agent or MCP clients) keep working
    across fixtures, runs and tests.

    Args:
        threshold: Minimum average score that must be achieved in order to pass the test.
        n: Number of times to run the test (if -1, uses Samples length)
        should_fail: If True, the test passes when the score is BELOW the threshold (default: False)
        parallel: If True, all runs are executed concurrently (default: False).
            Async tests are awaited concurrently, sync tests run in a thread pool.
        stop_early: If True, stop executing runs as soon as the outcome is
            provably decided (default: False). Assumes scores lie in [0, 1],
            which is the scale the judge uses. Mutually exclusive with parallel.

    Example:
        @nondeterministic_fixture(n=10)
        def llm_output():
            return call_llm("Generate a greeting")

        @nondeterministic_test(threshold=0.8)
        def test_greeting(llm_output):
            return judge(llm_output, criterion="Contains 'hello' or 'hi'")

        @nondeterministic_test(threshold=0.8, should_fail=True)
        def test_no_profanity(llm_output):
            return judge(llm_output, criterion="Contains profanity")
    """
    if parallel and stop_early:
        raise ValueError(
            "parallel and stop_early are mutually exclusive: "
            "early stopping decisions require sequential run results."
        )

    def decorator(func: Callable) -> Callable:
        is_async = asyncio.iscoroutinefunction(func)
        is_method = _expects_self(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> None:
            # Handle class methods by removing 'self' or 'cls' if present
            instance_or_class = None
            if is_method and args:
                instance_or_class = args[0]
                args = args[1:]

            # n_runs can be either given by n or defined by the length of the
            # Samples data in args or kwargs
            sample_data = next(
                (a for a in (*args, *kwargs.values()) if isinstance(a, Samples)),
                None,
            )
            if n > 0:
                n_runs = n
            elif sample_data is not None:
                n_runs = len(sample_data)
            else:
                raise RuntimeError(
                    "Cannot determine number of runs for nondeterministic_test. "
                    "Provide a nondeterministic fixture returning Samples or set n explicitly."
                )

            def build_call(i: int):
                # If we have sample data, pass the i-th element; plain lists pass through
                call_args = [
                    a[i] if isinstance(a, Samples) and len(a) == n_runs else a
                    for a in args
                ]
                call_kwargs = {
                    k: (v[i] if isinstance(v, Samples) and len(v) == n_runs else v)
                    for k, v in kwargs.items()
                }
                # Re-add 'self' or 'cls' if it was removed
                if instance_or_class is not None:
                    call_args = [instance_or_class] + call_args
                return call_args, call_kwargs

            def run_one(i: int) -> tuple[float, str]:
                try:
                    call_args, call_kwargs = build_call(i)
                    return _to_score(func(*call_args, **call_kwargs))
                except AssertionError as e:
                    return 0.0, str(e)
                except Exception as e:
                    return 0.0, f"{type(e).__name__}: {e}"

            async def run_one_async(i: int) -> tuple[float, str]:
                try:
                    call_args, call_kwargs = build_call(i)
                    return _to_score(await func(*call_args, **call_kwargs))
                except AssertionError as e:
                    return 0.0, str(e)
                except Exception as e:
                    return 0.0, f"{type(e).__name__}: {e}"

            # Run the test n times
            outcomes: list[tuple[float, str]]
            if parallel:

                async def _run_parallel():
                    if is_async:
                        return await asyncio.gather(
                            *[run_one_async(i) for i in range(n_runs)]
                        )
                    loop = asyncio.get_running_loop()
                    return await asyncio.gather(
                        *[
                            loop.run_in_executor(None, functools.partial(run_one, i))
                            for i in range(n_runs)
                        ]
                    )

                outcomes = list(run_coroutine(_run_parallel()))
            elif is_async:

                async def _run_sequential_async():
                    results = []
                    for i in range(n_runs):
                        results.append(await run_one_async(i))
                        if stop_early and _decision_final(
                            [s for s, _ in results], n_runs, threshold, should_fail
                        ):
                            break
                    return results

                outcomes = run_coroutine(_run_sequential_async())
            else:
                outcomes = []
                for i in range(n_runs):
                    outcomes.append(run_one(i))
                    if stop_early and _decision_final(
                        [s for s, _ in outcomes], n_runs, threshold, should_fail
                    ):
                        break

            scores = [s for s, _ in outcomes]
            reasons = [r for _, r in outcomes if r != ""]
            last_error_info = reasons[-1] if reasons else ""
            executed = len(outcomes)
            successes = sum(1 for s in scores if s >= threshold)

            # Calculate success rate; un-executed runs (stop_early) count as 0
            success_rate = successes / executed
            achieved_score = sum(scores) / n_runs

            passed = (
                achieved_score < threshold
                if should_fail
                else achieved_score >= threshold
            )
            record_result(
                name=getattr(func, "__qualname__", repr(func)),
                planned=n_runs,
                executed=executed,
                successes=successes,
                score=achieved_score,
                threshold=threshold,
                should_fail=should_fail,
                passed=passed,
                scores=scores,
            )

            # Assert the success rate meets the threshold
            error_info_text = f", {last_error_info}" if last_error_info != "" else ""
            stopped_early_text = (
                f", stopped early after {executed}/{n_runs} runs"
                if executed < n_runs
                else ""
            )
            run_scores_text = f", run scores: [{', '.join(f'{s:.2f}' for s in scores)}]"
            if should_fail:
                # For should_fail tests, we expect the score to be BELOW the threshold
                assert achieved_score < threshold, (
                    f"Test expected to fail but succeeded. "
                    f"Score: {achieved_score:.2} (required: < {threshold:.2}), "
                    f"Success rate: {success_rate:.2%} ({successes}/{executed})"
                    f"{stopped_early_text}{run_scores_text}{error_info_text}"
                )
            else:
                # Normal tests expect the score to be AT OR ABOVE the threshold
                assert achieved_score >= threshold, (
                    f"Test failed to meet success threshold. "
                    f"Score: {achieved_score:.2} (required: {threshold:.2}), "
                    f"Success rate: {success_rate:.2%} ({successes}/{executed})"
                    f"{stopped_early_text}{run_scores_text}{error_info_text}"
                )

        return pytest.mark.nondeterministic(wrapper)

    return decorator
