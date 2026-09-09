"""
Pytest plugin for quack-test: marker registration and session summary.
"""

from dataclasses import dataclass

from quack_test._runtime import close_event_loop


@dataclass
class QuackResult:
    """Recorded outcome of a single nondeterministic test."""

    name: str
    planned: int
    executed: int
    successes: int
    score: float
    threshold: float
    should_fail: bool
    passed: bool
    scores: list[float]


_results: list[QuackResult] = []


def record_result(**kwargs) -> None:
    """Record the outcome of a nondeterministic test for the session summary."""
    _results.append(QuackResult(**kwargs))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "nondeterministic: tests using quack-test's nondeterministic_test; "
        "deselect with '-m \"not nondeterministic\"'.",
    )


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not _results:
        return
    terminalreporter.write_sep("=", "quack-test summary")
    for r in _results:
        required = f"< {r.threshold:.2f}" if r.should_fail else f">= {r.threshold:.2f}"
        verdict = "PASS" if r.passed else "FAIL"
        stopped = (
            f", stopped early after {r.executed}/{r.planned} runs"
            if r.executed != r.planned
            else ""
        )
        run_scores = ", ".join(f"{s:.2f}" for s in r.scores)
        terminalreporter.write_line(
            f"{verdict} {r.name}: score {r.score:.2f} (required {required}), "
            f"{r.successes}/{r.executed} runs succeeded{stopped}, "
            f"run scores: [{run_scores}]"
        )


def pytest_sessionfinish(session, exitstatus):
    """Close the shared event loop once the session is done."""
    close_event_loop()
