"""System configuration for the voice assistant"""

from typing import Dict, Any

# Default conversation settings
DEFAULT_CONVERSATION_SETTINGS = {
    "max_turns": 20,
    "greeting_message": "Hello! Welcome to our automotive assistant. May I know your name, please?",
    "farewell_message": "Thank you for using our Automotive Assistant. Goodbye!",
    "timeout_seconds": 300, # 5 minutes
}

def get_system_config() -> Dict[str, Any]:
    """
    Return the complete system configuration.

    Returns:
        Dict containing all system configuration.
    """

    return {
        "conversation": DEFAULT_CONVERSATION_SETTINGS,
    }