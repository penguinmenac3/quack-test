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
from quack_test import nondeterministic_fixture, nondeterministic_test

@nondeterministic_fixture(n=5)
def sample_text():
    return f"{random.randint(1, 10)} apples."

@nondeterministic_test(threshold=0.8)
def test_simple_assertion(sample_text):
    apples = float(sample_text.split(" "))
    assert apples > 1, f"Expected more than 1 apple found {apples}."
```

In practice choosing `n=4` or `n=5` is recommended. The threshold should be then `0.75` or `0.8`, allowing for a single failure.
If you are choosing a bigger n, you are rather running a benchmark than just a test.
Here we assume, that if a feature is really broken, it does not only fail once, but more often.
On the other side, if a feature works robustly, it will should not fail or at maximum once.

### Judging via LLM

In many cases it is hard to evaluate with code, if an answer is actually correct.
In those cases, use a judge.

```python
from quack_test import judge, nondeterministic_test
# [...]

@nondeterministic_test(threshold=0.8)
def test_judge_with_criterion(sample_text):
    return judge(sample_text, criterion="More than 1 apple")

@nondeterministic_test(threshold=0.8)
def test_judge_with_gt(sample_text):
    return judge(sample_text, gt="N (0-10) apples")
```

### Class Based Tests

Testing in classes can be beneficial in some use-cases. This is not hindered by quack-test.

```python
class TestClassBased:
    @nondeterministic_test(n=3, threshold=0.2)
    def test_assert_only(self):
        # You can also create your own score and explanation
        return random.random(), "The expected value is above 0.2, but was lower."
```

### Negative Tests

Writing negative tests that must fail is important.
In quack test, you can simply specify that a test has to fail via `should_fail=True`.

```python
@nondeterministic_test(threshold=0.8, should_fail=True)
def test_negative(sample_text):
    return judge(sample_text, criterion="Has only coal")
```

### Showcase for Error Messages

The following example code will fail and cause an error message.

```python
@nondeterministic_test(threshold=0.8)
def test_assertion_demo_failure(sample_text):
    assert False, "This message is shown in the pytest summary."
    # -> FAILED test/test_example.py::test_assertion_demo_failure - AssertionError: Test failed to meet success threshold. Score: 0.0 (required: 0.8), Success rate: 0.00% (0/5), This message is shown in the pytest summary.

@nondeterministic_test(threshold=0.8)
def test_judge_demo_failure(sample_text):
    return judge(sample_text, criterion="Has only coal")
    # -> FAILED test/test_example.py::test_judge_demo_failure - AssertionError: Test failed to meet success threshold. Score: 0.0 (required: 0.8), Success rate: 0.00% (0/5), Text: '3 apples.' Criterion: 'Has only coal'
```

### Advanced Judge Setup

If you do not want to setup the judge via the `.env` file as shown above, you can also set it up via code.
In this example we hardcode a local ollama instance.
Of course you should NEVER put your api key in the code, but if you manage your secrets differently than in a `.env` this can come in clutch to pass your secrets to the judge.

```python
def setup_module():
    configure_judge(
        provider="OpenAI",
        api_key="ollama",
        model_name="qwen3:4b",
        endpoint="http://localhost:11434/v1"
    )
```

Have fun quack testing your agents!
