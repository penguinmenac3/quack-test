PROMPT_CRITERION = """Evaluate the following text based on the criterion.

Criterion: {criterion}

Return a score between 0.0 and 1.0 indicating how well the text meets the criterion. Only respond with a single number.
"""

PROMPT_GT = """Evaluate how similar the following text is to the ground truth.

Ground Truth: {gt}

Return a score between 0.0 and 1.0 indicating how similar they are. Only respond with a single number.
"""
