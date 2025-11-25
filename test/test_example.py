import random
from quack_test import nondeterministic_fixture, nondeterministic_test, judge


@nondeterministic_fixture(n=5)
def sample_text():
    return f"I have {random.randint(0, 10)} apples."


@nondeterministic_test(threshold=0.8)
def test_apples(sample_text):
    return judge(sample_text, criterion="Has more than 1 apple")


@nondeterministic_test(threshold=0.8)
def test_apples_gt(sample_text):
    return judge(sample_text, gt="I have N (0-10) apples")


@nondeterministic_test(threshold=0.8, should_fail=True)
def test_coal(sample_text):
    return judge(sample_text, criterion="Has only coal")
