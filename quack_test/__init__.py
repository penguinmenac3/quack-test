"""
Quack Test - Decorators for handling nondeterministic tests and fixtures.

Provides decorators for running fixtures and tests multiple times to handle
flaky behavior, particularly useful for LLM-based tests.
"""

from quack_test.decorators import nondeterministic_fixture, nondeterministic_test
from quack_test.judge import judge

__all__ = [
    "nondeterministic_fixture",
    "nondeterministic_test",
    "judge",
]
