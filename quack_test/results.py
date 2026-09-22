"""Result types for nondeterministic evaluations."""

from dataclasses import dataclass, field


@dataclass
class EvaluationResult:
    """Score, explanation, and structured per-run evaluation metrics."""

    score: float
    reason: str = ""
    metrics: dict[str, object] = field(default_factory=dict)
