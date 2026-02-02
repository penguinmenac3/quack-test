from quack_test import nondeterministic_test
import random


class TestClassBased:
    @nondeterministic_test(n=3, threshold=0.2)
    def test_assert_only(self):
        # You can also create your own score and explanation
        return random.random(), "The expected value is above 0.2, but was lower."
