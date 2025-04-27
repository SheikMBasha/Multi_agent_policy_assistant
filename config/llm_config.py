import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional

load_dotenv()

def get_llm_config(temperature: float = 0.7) -> Dict[str,Any]:
    """
    Return a standard LLM configuration.
    Args:
        temperature: Temperature setting for the LLM (0.0 to 1.0)

    Returns:
        Dict containing LLM configuration.
    """

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not OPENAI_API_KEY:
        raise ValueError("OpenAI_API_KEY environment variable not set.")

    llm_config = {
        "config_list": [{"model": "gpt-3.5-turbo", "api_key": OPENAI_API_KEY}],
        "temperature": 0.3,
        "cache_seed": None  # 👈 Disable cache
    }

    return llm_config

