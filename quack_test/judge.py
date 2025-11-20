"""
Judge function for evaluating test outputs against criteria.
"""
import os
from functools import cache
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI, AzureOpenAI

# Load environment variables
load_dotenv()

# Get the directory where this file is located
_PROMPTS_DIR = Path(__file__).parent


@cache
def _load_prompt_template(filepath: Path) -> str:
    """Load a prompt template from a markdown file with caching."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


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
    text: str, 
    criterion: str = "", 
    gt: str = "", 
    prompt_template: Optional[str] = None
) -> float:
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
    
    Examples:
        >>> judge("I have 5 apples", criterion="Has more than 1 apple")
        5.0
        
        >>> judge("I have coal", gt="I have some coal")
        5.0
        
        >>> judge("No apples here", criterion="Has more than 1 apple")
        0.0
        
        >>> judge("I have 5 apples", criterion="Has apples", 
        ...       prompt_template="Does '{text}' meet '{criterion}'? Score 0-1:")
        5.0
    """    
    # Build the prompt based on what's provided
    if prompt_template:
        # Use custom prompt template
        prompt = prompt_template.format(criterion=criterion, gt=gt)
    elif criterion and gt:
        raise ValueError("Criterion and gt cannot be set at the same time without a custom template.")
    elif criterion:
        # Load criterion prompt template
        template = _load_prompt_template(_PROMPTS_DIR / "prompt_criterion.md")
        prompt = template.format(criterion=criterion)
    elif gt:
        # Load ground truth prompt template
        template = _load_prompt_template(_PROMPTS_DIR / "prompt_gt.md")
        prompt = template.format(gt=gt)
    else:
        raise ValueError("Either criterion or gt must be provided")
    
    # Make the API call
    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"),
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
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
        return score
    except ValueError:
        raise ValueError(f"Failed to parse score from response: {score_text}")
