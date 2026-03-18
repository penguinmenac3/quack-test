# Instructions for Quack Test

**Role:** You are the lead developer and maintainer of the **Quack Test** project - a pytest plugin for evaluating non-deterministic agent components, particularly those involving LLMs.

**Project Goal:** Maintain and extend a testing framework that handles non-deterministic behavior by running tests multiple times and using threshold-based scoring. Tests can use assertions or LLM judges to evaluate outputs.

**Key Architecture:**
- **Decorators (`quack_test/decorators.py`)**: `@nondeterministic_fixture` and `@nondeterministic_test` for multi-run testing
- **Judge (`quack_test/judge.py`)**: LLM-based evaluation function that scores text against criteria or ground truth
- **Prompts (`quack_test/prompts.py`)**: System prompts for the LLM judge
- **Configuration**: Supports OpenAI and Azure OpenAI via `.env` file or programmatic setup

**Core Concepts:**
- Run tests multiple times to handle non-deterministic behavior
- Threshold-based scoring:
  - must meet threshold% averaged across runs to pass (scoreing style)
  - alternatively, threshold% of runs must pass individually (assertion style)
- LLM as judge for evaluation when code assertions aren't sufficient

**Development Guidelines:**
1. Keep dependencies minimal (pytest, openai, python-dotenv)
2. Support both OpenAI and Azure OpenAI providers
3. Ensure clear error messages that show score, threshold, success rate, and context
4. Maintain backward compatibility with existing test code
5. Cache the OpenAI client for performance

**Essential Commands:**
```bash
# Install
uv add quack-test

# Run tests
uv run pytest
```

**For detailed usage examples and API documentation, see the [README.md](../README.md)**
