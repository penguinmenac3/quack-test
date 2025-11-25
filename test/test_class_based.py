from quack_test import nondeterministic_test
import random


class TestClassBased:
    @nondeterministic_test(n=3, threshold=0.2)
    def test_assert_only(self):
        # Assert-only tests in classes should be treated as successful runs
        return random.random()
