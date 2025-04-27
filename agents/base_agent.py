"""Base agent implementation for all specialized agents"""

import json
import autogen
from typing import Dict, Any
from context.conversation_context import ConversationContext

class SimplifiedAgent:
    """Base class for all simplified agents that combine agent and handler functionality"""

    def __init__(self, name: str, system_message: str, llm_config: Dict[str, Any], context: ConversationContext):
        self.name = name
        self.system_message = system_message
        self.llm_config = llm_config
        self.context = context

        # Create the underlying autogen agent
        self.agent = autogen.AssistantAgent(
            name=name,
            system_message=system_message,
            llm_config=llm_config
        )

    def generate_response(self, message: str) -> str:
        """Generate a response to the user message"""
        # Extract information from message
        self._extract_info_from_message(message)

        # Enrich message with context
        enriched_message = self._enrich_with_context(message)

        # Generate response using the underlying agent
        response = self.agent.generate_reply(enriched_message)

        # Personalize the response
        personalized_response = self.context.personalize(response)

        # Update conversation history
        self.context.add_to_history(self.name, personalized_response)

        return personalized_response

    def _extract_info_from_message(self, message: str) -> None:
        """Extract information from the message - overridden by subclasses"""
        # Base implementation just extracts name, location, and contact info
        name = self.context.extract_name(message)
        if name and not self.context.user_name:
            self.context.user_name = name

        location = self.context.extract_location(message)
        if location and not self.context.user_location:
            self.context.user_location = location

        contact = self.context.extract_contact_info(message)
        if contact and not self.context.user_contact_info:
            self.context.user_contact_info = contact

    def _enrich_with_context(self, message: str) -> str:
        """Add context information to the message"""
        # Gather context information
        context_info = {}

        # Add user information
        if self.context.user_name:
            context_info["user_name"] = self.context.user_name
        if self.context.user_location:
            context_info["user_location"] = self.context.user_location
        if self.context.user_contact_info:
            context_info["user_contact_info"] = self.context.user_contact_info

        # Add conversation information
        context_info["conversation_turns"] = self.context.turns_count
        if self.context.last_active_agent:
            context_info["last_active_agent"] = self.context.last_active_agent

        # Add recent message history
        recent_messages = self.context.get_recent_messages(3)
        if recent_messages:
            context_info["recent_conversation"] = [
                f"{msg['sender']}: {msg['message']}" for msg in recent_messages
            ]

        # Format as a structured prefix
        if context_info:
            context_prefix = f"[CONTEXT]\n{json.dumps(context_info, indent=2)}\n[/CONTEXT]\n\n"
            return context_prefix + message
        else:
            return message