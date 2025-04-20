import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Missing OPENAI_API_KEY in .env file.")

llm_config = {
    "config_list": [{"model": "gpt-3.5-turbo", "api_key": OPENAI_API_KEY}],
    "temperature": 0.3,
    "cache_seed": None,  # 👈 Disable cache
}