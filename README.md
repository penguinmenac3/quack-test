# Quack Test

A plugin for pytest to evaluate non-deterministic agent components.

![A runber duckie taking a test](quack-test.jpg)

## Installation & Setup

Simply pip install it.

```bash
pip install quack-test
```

To use the LLM judge you will need to add the required config to your `.env` file.

```bash
# OpenAI Provider Configuration
# Set to "OpenAI" or "AzureOpenAI"
OPENAI_PROVIDER=OpenAI

# Unified Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL_NAME=gpt-4
OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
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
