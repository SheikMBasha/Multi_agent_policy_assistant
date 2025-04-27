"""Moderator agent implementation for routing queries to specialized agents"""

import traceback
from typing import Dict, Any, List
from agents.base_agent import SimplifiedAgent
from context.conversation_context import ConversationContext

class ModeratorAgent(SimplifiedAgent):
    """Determines which specialist agent should handle the query"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext):
        super().__init__(
            name="ModeratorAgent",
            system_message="""
You are the RouterAgent for a dealer voice assistant. Based on the user query, You determine which agent should respond to the user query.

- @PricingAgent: Calculates the dealer compensation based on dealer name. It is the agent which will return the final answer.
- @PolicyAgent: Use if the user is asking about loan policies, rules, required documents, eligibility, term length, maximum age, conditions, or approval criteria.
- @DealerAgent: Use if the user wants to log a complaint, report an issue, or give feedback about the dealership experience.

DO NOT respond or explain — just tag the appropriate agent with the full user query.

Examples:
- "What documents do I need?" → PolicyAgent
- "What's the current APR on a hatchback?" → PricingAgent
- "The dealer was rude to me" → DealerAgent
- "What is the loan term length?" → PolicyAgent
- "Dealership or Dealer is or Dealership Name is or Dealer Name is: " -> PricingAgent
# Be Precise and respond with ONLY the agent name.
            """,
            llm_config=llm_config,
            context=context
        )

    def determine_agent(self, message: str) -> str:
        """Determine which agent should handle the message"""

        try:
            # Create a proper message list according to Autogen's expectations
            messages = [
                {
                    "role": "user",
                    "content": f"User query: {message}"
                }
            ]
            
            # Call the proper method with the message list
            response = self.agent.generate_reply(messages=messages)
            
            # Default to SmallTalk if no clear match
            valid_agents = ["PricingAgent", "PolicyAgent", "DealerAgent", "SmallTalkAgent"]
            for agent in valid_agents:
                if agent in response:
                    return agent
                    
            return "SmallTalkAgent"
        except Exception as e:
            print(f"DETAILED ERROR in moderator agent: {type(e)}, {e}")
            print(traceback.format_exc())
            
            # Temporary fallback
            if "loan" in message.lower():
                return "PricingAgent"
            return "SmallTalkAgent"