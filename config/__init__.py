"""Configuration module for the voice assistant"""

from config.llm_config import get_llm_config
from config.system_config import get_system_config

__all__ = ['get_llm_config', 'get_system_config']