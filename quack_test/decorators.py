"""
Decorators for handling nondeterministic tests and fixtures.
"""

import functools
import pytest
from typing import Callable, Any, List


def nondeterministic_fixture(n: int = 5):
    """
    Decorator for fixtures that should be executed multiple times.

    The fixture function will be executed `n` times, and all results
    will be collected into a list. This list is then passed to tests
    that depend on this fixture.

    Args:
        n: Number of times to execute the fixture (default: 5)

    Example:
        @nondeterministic_fixture(n=10)
        def random_data():
            return random.randint(1, 100)

        # The test will receive a list of 10 random integers
        def test_values(random_data):
            assert len(random_data) == 10
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> List[Any]:
            results = []
            for _ in range(n):
                result = func(*args, **kwargs)
                results.append(result)
            return results

        # Mark this as a pytest fixture
        return pytest.fixture(wrapper)

    return decorator


def nondeterministic_test(
    threshold: float = 0.8, n: int = -1, should_fail: bool = False
):
    """
    Decorator for tests that should be executed multiple times with a success threshold.

    The test function will be executed multiple times (determined by the length of
    fixture data if available, or a default number). The test must return a score
    which will be averaged. If the average score is higher than the given threshold, you pass.

    Args:
        threshold: Minimum average score that must be achieved in order to pass the test.
        n: Number of times to run the test (if -1, uses fixture length)
        should_fail: If True, the test passes when the score is BELOW the threshold (default: False)

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

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> None:
            # Handle class methods by skipping 'self' or 'cls' if present
            if len(args) > 0 and hasattr(args[0], "__class__"):
                instance_or_class = args[0]
                args = args[1:]  # Remove 'self' or 'cls' from args
            else:
                instance_or_class = None

            # n_runs can be either given by n or defined by the length of the fixture data in args or kwargs
            fixture_data = None
            for arg in args:
                if isinstance(arg, list):
                    fixture_data = arg
                    break
            for kwarg in kwargs.values():
                if isinstance(kwarg, list):
                    fixture_data = kwarg
                    break
            if n > 0:
                n_runs = n
            elif fixture_data is not None:
                n_runs = len(fixture_data)
            else:
                raise RuntimeError(
                    "Cannot determine number of runs for nondeterministic_test. "
                    "Provide a fixture that returns a list or set n explicitly."
                )

            # Run the test n times
            successes = 0
            failures = 0
            scores = []
            last_error_info = ""

            for i in range(n_runs):
                try:
                    # If we have fixture data, pass the i-th element
                    test_args = [
                        arg[i] if isinstance(arg, list) and len(arg) == n_runs else arg
                        for arg in args
                    ]
                    test_kwargs = {
                        k: (v[i] if isinstance(v, list) and len(v) == n_runs else v)
                        for k, v in kwargs.items()
                    }

                    # Re-add 'self' or 'cls' if it was removed
                    if instance_or_class is not None:
                        test_args = [instance_or_class] + test_args

                    try:
                        result = func(*test_args, **test_kwargs)
                        if result is None:
                            result = 1.0, ""
                        if isinstance(result, float):
                            result = result, ""
                        if isinstance(result, str):
                            result = 1.0, result
                    except AssertionError as e:
                        last_error_info = str(e)
                        result = 0.0, str(e)
                    score, reason = result
                    scores.append(score)
                    if reason != "":
                        last_error_info = reason

                    if score > threshold:
                        successes += 1
                    else:
                        failures += 1
                except Exception:
                    failures += 1
                    scores.append(0)

            # Calculate success rate
            success_rate = successes / n_runs
            achieved_score = sum(scores) / n_runs

            # Assert the success rate meets the threshold
            error_info_text = f", {last_error_info}" if last_error_info != "" else ""
            if should_fail:
                # For should_fail tests, we expect the score to be BELOW the threshold
                assert achieved_score < threshold, (
                    f"Test expected to fail but succeeded. "
                    f"Score: {achieved_score:.2} (required: < {threshold:.2}), "
                    f"Success rate: {success_rate:.2%} ({successes}/{n_runs})"
                    f"{error_info_text}"
                )
            else:
                # Normal tests expect the score to be AT OR ABOVE the threshold
                assert achieved_score >= threshold, (
                    f"Test failed to meet success threshold. "
                    f"Score: {achieved_score:.2} (required: {threshold:.2}), "
                    f"Success rate: {success_rate:.2%} ({successes}/{n_runs})"
                    f"{error_info_text}"
                )

        return wrapper

    return decorator
