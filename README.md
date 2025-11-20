# Quack Test

A plugin for pytest to evaluate non-deterministic agent components.

## Installation

Simply pip install it

```bash
pip install quack-test
```

## Run tests

Simply run your tests using pytest (quack_tests are just pytests)

```bash
pytest
```

## Writing Tests

You can simply specify `@nondeterministic` for components, which are not deterministic and should be run multiple times.
Implement everything in a `test_*.py` file in your `test` or `tests` folder.

```python
import random
from quack_test import nondeterministic_fixture, nondeterministic_test, judge

@nondeterministic_fixture(n=5)
def sample_text():
    return f"I have {random.randint(1, 10)} apples."

@nondeterministic_test(score=0.8)
def test_apples(sample_text):
    return judge(sample_text, criterion="Has more than 1 apple")

@nondeterministic_test(score=0.8)
def test_apples_gt(sample_text):
    return judge(sample_text, gt="I have N (0-10) apples")

@nondeterministic_test(score=0.8, should_fail=True)
def test_coal(sample_text):
    return judge(sample_text, criterion="Has only coal")
```
