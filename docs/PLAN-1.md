## Goal
Implement decorators for running fixtures and tests multiple times (n times), enabling collection of multiple samples from fixtures and result aggregation with scoring.

## Current State
No existing code base. We are setting up the implementation of both decorators from scratch, with compatibility for pytest and unittest frameworks.

## Plan

- [ ] Create Module Structure:
  - Establish `quack_test/` as the main module directory.
  - Ensure inclusion of necessary files for fixture and test functionalities.
- [ ] Define Decorator `nondeterministic_fixture(n)`:
  - This decorator will wrap a fixture function.
  - Execute the wrapped fixture `n` times and store all results in a list.
  - Return the list of results to ensure multiple sample outcomes are available for testing.
  - Ensure compatibility with pytest and unittest, specifically in fixture setup and teardown phases.
- [ ] Define Decorator `nondeterministic_test(threshold)`:
  - This decorator will wrap a test function.
  - Execute the wrapped test function `n` times.
  - Collect and calculate a score based on the test results (e.g., pass/fail tally).
  - Assert the calculated score against the provided threshold (`threshold`) to determine test success or failure.
  - Maintain compatibility with pytest and unittest, integrating seamlessly with result reporting and assertion mechanics.
- [ ] Create `judge()` Functionality:
  - Develop the logic needed to assess test output against specific conditions.
  - Enable flexible evaluation methods, including simple comparison and regular expressions.
- [ ] Leverage Existing Example Tests:
  - Utilize `test/test_example.py` to showcase and validate new functionality.
  - Use the existing example test to ensure correct and expected behavior across edge cases and normal execution.

## Acceptance Criteria
- [ ] Nondeterministic fixtures execute `n` times and return lists of results compatible with both pytest and unittest frameworks.
- [ ] Tests execute `n` times independently and adhere to scoring criteria, demonstrating correct aggregation of results and outcome assessment.
- [ ] Compatibility with both pytest and unittest.
- [ ] Successful execution and validation of example tests within both contexts.
