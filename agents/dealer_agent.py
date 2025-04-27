"""Dealer agent implementation for handling dealer-related queries"""

from typing import Dict, Any
from agents.base_agent import SimplifiedAgent
from context.conversation_context import ConversationContext

class DealerAgent(SimplifiedAgent):
    """Handles dealer related queries and human escalation"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext):
        super().__init__(
            name="DealerAgent",
            system_message="""
You are the DealerAgent.

Your job is to handle complaints and issues raised by car dealers. If the user reports a missing payment, issue with an application, or any service delay:

1. Acknowledge the problem
2. Confirm a ticket has been created
3. Politely mention that you're transferring them to a human executive
4. End every response with: [final_answer]

Example:
"Thank you for your request. We have created a ticket. Please be online while we transfer your call to our executive. [final_answer]"
""",
            llm_config=llm_config,
            context=context
        )

    def generate_response(self, message: str) -> str:
        # You can customize here if needed
        enriched_message = f"This is a dealer assistant agent question. {message}"

        messages = [{"role": "user", "content": enriched_message}]
        response = self.agent.generate_reply(messages=messages)
        personalized_response = self.context.personalize(response)
        self.context.add_to_history(self.name, personalized_response)

        return personalized_response

    def _extract_info_from_message(self, message: str) -> None:
        """Extract and save dealer-related information from the message"""
        super()._extract_info_from_message(message)
        
        message_lower = message.lower()

        if any(word in message_lower for word in ["speak", "human", "person", "representative", "talk to"]):
            self.context.escalation_requested = True