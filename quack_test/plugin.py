"""
Pytest plugin for quack-test: marker registration, session summary, and CSV export.
"""

import csv
import json
import numbers
import os
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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
    reasons: list[str]
    metrics: list[dict[str, object]]


_results: list[QuackResult] = []
_current_test_name: ContextVar[str | None] = ContextVar("quack_test_name", default=None)

_METRIC_COLUMN_ORDER = (
    "time_to_first_token_s",
    "duration_s",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "output_chunks",
    "answer",
)


def record_result(**kwargs) -> None:
    """Record the outcome of a nondeterministic test for the session summary."""
    test_name = _current_test_name.get()
    if test_name:
        kwargs["name"] = test_name
    _results.append(QuackResult(**kwargs))


def pytest_addoption(parser) -> None:
    group = parser.getgroup("quack-test")
    group.addoption(
        "--quack-results-dir",
        action="store",
        default=os.getenv("QUACK_RESULTS_DIR", "."),
        help="Directory for timestamped quack-test CSV results.",
    )


def pytest_runtest_call(item) -> None:
    _current_test_name.set(item.nodeid)


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


def _metric_keys() -> list[str]:
    keys = {
        str(key)
        for result in _results
        for run_metrics in result.metrics
        for key in run_metrics
    }
    return [
        *[key for key in _METRIC_COLUMN_ORDER if key in keys],
        *sorted(keys - set(_METRIC_COLUMN_ORDER)),
    ]


def _is_numeric_metric(value: object) -> bool:
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def _numeric_metric_keys(metric_keys: list[str]) -> list[str]:
    return [
        key
        for key in metric_keys
        if any(
            _is_numeric_metric(run_metrics.get(key))
            for result in _results
            for run_metrics in result.metrics
        )
    ]


def _serialize_metric(value: object) -> object:
    """Convert a metric into a CSV-safe scalar while preserving useful data."""
    if value is None:
        return ""
    if isinstance(value, (str, numbers.Real, bool)):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _write_csv_results(results_dir: str) -> Path:
    output_dir = Path(results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_path = output_dir / f"{timestamp}_quack-test-results.csv"
    max_runs = max(len(result.scores) for result in _results)
    metric_keys = _metric_keys()
    numeric_metric_keys = _numeric_metric_keys(metric_keys)
    fieldnames = [
        "test_name",
        "planned_runs",
        "executed_runs",
        "successful_runs",
        "overall_score",
        "threshold",
        "should_fail",
        "passed",
    ]
    for run_number in range(1, max_runs + 1):
        fieldnames.extend((f"run_{run_number}_score", f"run_{run_number}_reason"))
        fieldnames.extend(
            f"run_{run_number}_{metric_key}" for metric_key in metric_keys
        )
    fieldnames.extend(f"mean_{metric_key}" for metric_key in numeric_metric_keys)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for result in _results:
            row = {
                "test_name": result.name,
                "planned_runs": result.planned,
                "executed_runs": result.executed,
                "successful_runs": result.successes,
                "overall_score": result.score,
                "threshold": result.threshold,
                "should_fail": result.should_fail,
                "passed": result.passed,
            }
            for index, score in enumerate(result.scores):
                run_number = index + 1
                row[f"run_{run_number}_score"] = score
                row[f"run_{run_number}_reason"] = result.reasons[index]
                for metric_key in metric_keys:
                    if metric_key in result.metrics[index]:
                        row[f"run_{run_number}_{metric_key}"] = _serialize_metric(
                            result.metrics[index][metric_key]
                        )
            for metric_key in numeric_metric_keys:
                values = [
                    run_metrics[metric_key]
                    for run_metrics in result.metrics
                    if _is_numeric_metric(run_metrics.get(metric_key))
                ]
                if values:
                    row[f"mean_{metric_key}"] = sum(values) / len(values)
            writer.writerow(row)
    return output_path


def pytest_sessionfinish(session, exitstatus):
    """Write CSV results and close the shared event loop once the session is done."""
    if _results:
        output_path = _write_csv_results(
            session.config.getoption("--quack-results-dir")
        )
        session.config.pluginmanager.get_plugin("terminalreporter").write_line(
            f"quack-test CSV results: {output_path}"
        )
    close_event_loop()
