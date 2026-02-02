import random
from quack_test import configure_judge, nondeterministic_fixture, nondeterministic_test, judge

# OPTIONAL: Setup function to configure the judge before tests run
# in case you do not want to rely on the `.env` file.
def setup_module():
    configure_judge()


# Create a nondeterministic fixture, so that it is only executed once for all tests
# putting your agent in here is recommended to reduce overhead.
@nondeterministic_fixture(n=5)
def sample_text():
    return f"{random.randint(1, 10)} apples."


# Simple Assert only test
@nondeterministic_test(threshold=0.8)
def test_simple_assertion(sample_text):
    apples = float(sample_text.split(" ")[0])
    assert apples > 1, f"Expected more than 1 apple found {apples}."


# LLM as a judge tests
@nondeterministic_test(threshold=0.8)
def test_judge_with_criterion(sample_text):
    return judge(sample_text, criterion="More than 1 apple")


@nondeterministic_test(threshold=0.8)
def test_judge_with_gt(sample_text):
    return judge(sample_text, gt="N (0-10) apples")


# Negative tests
@nondeterministic_test(threshold=0.8, should_fail=True)
def test_negative(sample_text):
    return judge(sample_text, criterion="Has only coal")


# Showcase error messages
# @nondeterministic_test(threshold=0.8)
# def test_assertion_demo_failure(sample_text):
#     assert False, "This message is shown in the pytest summary."


# @nondeterministic_test(threshold=0.8)
# def test_judge_demo_failure(sample_text):
#     return judge(sample_text, criterion="Has only coal")
