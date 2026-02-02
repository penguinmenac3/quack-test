"""
Judge function for evaluating test outputs against criteria.
"""
import os
from functools import cache
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI, AzureOpenAI

from quack_test.prompts import PROMPT_CRITERION, PROMPT_GT

# Load environment variables
load_dotenv()

def configure_judge(
    provider: str | None = None,
    api_key: str | None = None,
    endpoint: str | None = None,
    api_version: str | None = None,
    model_name: str | None = None,
) -> None:
    """Configure the judge by setting environment variables."""
    if provider:
        os.environ["OPENAI_PROVIDER"] = provider
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    if endpoint:
        os.environ["OPENAI_ENDPOINT"] = endpoint
    if api_version:
        os.environ["OPENAI_API_VERSION"] = api_version
    if model_name:
        os.environ["OPENAI_MODEL_NAME"] = model_name


@cache
def _get_client():
    """Create and cache the OpenAI or Azure OpenAI client."""
    provider = os.getenv("OPENAI_PROVIDER", "OpenAI")
    
    if provider == "AzureOpenAI":
        return AzureOpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_ENDPOINT"],
            api_version=os.getenv("OPENAI_API_VERSION", "2024-10-21"),
        )
    else:
        return OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_ENDPOINT"],
        )


def judge(
    text: str, criterion: str = "", gt: str = "", prompt_template: Optional[str] = None
) -> tuple[float, str]:
    """
    Evaluate whether an text meets a given criterion or matches the ground truth.

    Args:
        text: The text to evaluate (typically a string)
        criterion: (Optional) The criterion to check against
        gt: (Optional) A ground truth which the text should match
        prompt_template: (Optional) Custom prompt template string with {text}, {criterion}, and/or {gt} placeholders.
                        If not provided, loads from criterion_prompt.md or gt_prompt.md

    Returns:
        float: A score how well it matches the gt or criterion
        str: The original text (for debugging)

    Examples:
        >>> judge("I have 5 apples", criterion="Has more than 1 apple")
        5.0, "I have 5 apples"

        >>> judge("I have coal", gt="I have some coal")
        5.0, "I have coal"

        >>> judge("No apples here", criterion="Has more than 1 apple")
        0.0, "No apples here"

        >>> judge("I have 5 apples", criterion="Has apples",
        ...       prompt_template="Does '{text}' meet '{criterion}'? Score 0-1:")
        5.0, "I have 5 apples"
    """
    explanation = ""
    # Build the prompt based on what's provided
    if prompt_template:
        # Use custom prompt template
        prompt = prompt_template.format(criterion=criterion, gt=gt)
        explanation = f"Text: '{text}' Criterion: '{criterion}' GT: '{gt}'"
    elif criterion and gt:
        raise ValueError("Criterion and gt cannot be set at the same time without a custom template.")
    elif criterion:
        # Load criterion prompt template
        prompt = PROMPT_CRITERION.format(criterion=criterion)
        explanation = f"Text: '{text}' Criterion: '{criterion}'"
    elif gt:
        # Load ground truth prompt template
        prompt = PROMPT_GT.format(gt=gt)
        explanation = f"Text: '{text}' GT: '{gt}'"
    else:
        raise ValueError("Either criterion or gt must be provided")
    
    # Make the API call
    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
        temperature=0.0,
    )
    # Extract and return the score
    content = response.choices[0].message.content
    if content is None:
        raise ValueError("Received empty response from API")
    
    score_text = content.strip()
    try:
        score = float(score_text)
        # Clamp the score between 0.0 and 1.0
        return score, explanation
    except ValueError:
        raise ValueError(f"Failed to parse score from response: {score_text}")
