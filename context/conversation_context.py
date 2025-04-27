"""Conversation context management for the voice assistant"""

import re
import random
from typing import Dict, Any, Optional, List

class ConversationContext:
    """Manages shared context across all agents in the conversation."""

    def __init__(self):
        # User Information
        self.user_name: Optional[str] = None
        self.conversation_started: bool = False
        self.turns_count: int = 0
        self.last_active_agent: Optional[str] = None

        # User specific information
        self.user_location: Optional[str] = None
        self.user_contact_info: Optional[str] = None

        # Conversation History
        self.message_history: List[Dict[str, str]] = []

        # Domain-specific information
        self.contract_apr: Optional[float] = None
        self.buy_rate: Optional[float] = None
        self.policy_topic: Optional[str] = None
        self.dealer_name: Optional[str] = None
        self.escalation_requested: bool = False

    def add_to_history(self, sender: str, message: str) -> None:
        """Add a message to the conversation history"""
        self.message_history.append({
            "sender": sender,
            "message": message
        })
        self.turns_count += 1

    def extract_name(self, message: str) -> Optional[str]:
        """Try to extract a name from user message."""
        name_patterns = [
            r"(?:I am|I'm|my name is|this is|call me) (\w+)",
            r"(\w+) (?:here|speaking)",
            r"^(\w+)$"  # Just a single word could be a name
        ]

        for pattern in name_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                # Extract name and capitalize first letter
                name = match.group(1)
                return name[0].upper() + name[1:] if len(name) > 1 else name.upper()

        return None

    def extract_location(self, message: str) -> Optional[str]:
        """Try to extract a location from user message."""
        # Simple zip code extraction
        zip_match = re.search(r'\b\d{5}(?:-\d{4})?\b', message)
        if zip_match:
            return zip_match.group(0)

        # City, State format extraction
        city_state_match = re.search(r'([A-Za-z\s]+),\s*([A-Za-z]{2,})', message)
        if city_state_match:
            return f"{city_state_match.group(1)}, {city_state_match.group(2)}"

        return None

    def extract_contact_info(self, message: str) -> Optional[str]:
        """Extract contact information from message."""
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', message)
        if email_match:
            return email_match.group(0)

        phone_match = re.search(r'(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', message)
        if phone_match:
            return phone_match.group(0)

        return None

    def get_recent_messages(self, count: int = 3) -> List[Dict[str, str]]:
        """Get the most recent messages from history."""
        return self.message_history[-count:] if self.message_history else []

    def personalize(self, message: str) -> str:
        """Add personalization to message if user_name is known"""
        if not self.user_name:
            return message

        # If message already contains the name, don't add it again
        if self.user_name in message:
            return message

        # Add name to beginning occasionally
        if random.random() < 0.3:  # 30% chance
            greeting_phrases = [
                f"{self.user_name}, ",
                f"Well {self.user_name}, ",
                f"So {self.user_name}, ",
            ]
            prefix = random.choice(greeting_phrases)
            return prefix + message[0].lower() + message[1:] if message else ""

        return message