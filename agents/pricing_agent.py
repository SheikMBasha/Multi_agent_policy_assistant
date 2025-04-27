"""Pricing agent implementation for handling financial queries"""

import re
from typing import Dict, Any
from agents.base_agent import SimplifiedAgent
from context.conversation_context import ConversationContext
from tools.calculateincentivetool import CalculateIncentiveTool

class PricingAgent(SimplifiedAgent):
    """Handles pricing related queries"""

    def __init__(self, llm_config: Dict[str, Any], context: ConversationContext, incentive_tool: CalculateIncentiveTool):
        super().__init__(
            name="PricingAgent",
            system_message="""
You are the PricingAgent. You assist users in calculating dealer compensation.

🚨 CRITICAL INSTRUCTION:
You MUST end EVERY response with [final_answer]. This is required for proper conversation termination.

You have access to a function named `calculate_dealer_compensation(dealer_name: string)` which makes an API call and returns compensation information.

Behavior Instructions:
1. Always start by asking the user for the dealer name if not already provided.
2. Once you have the dealer name, call the tool `calculate_dealer_compensation(dealer_name)`.
3. After receiving the result, share the compensation value with the user.
4. ALWAYS end EVERY message with `[final_answer]`.
5. Remember values from earlier in the conversation unless the user updates them.

Examples of proper responses:

User: "I need to check compensation"
You: "I can help with that. What's the dealer name? [final_answer]"

User: "The dealer is ABC Motors"
You: *Call calculate_dealer_compensation("ABC Motors")*
Then respond: "Based on our records, the compensation for ABC Motors is $XXX. [final_answer]"

User: "Thanks"
You: "You're welcome! Let me know if you need anything else. [final_answer]"

Remember: ALWAYS include [final_answer] at the end of EVERY response without exception.
""",
            llm_config=llm_config,
            context=context
        )

        self.incentive_tool = incentive_tool

    def generate_response(self, message: str) -> str:
        self._extract_info_from_message(message)

        # Check what information is missing
        if self.context.dealer_name is None:
            return "Could you please provide the Dealer Name?"
        # if self.context.contract_apr is None:
        #     return "Could you please provide the contract APR?"

        # if self.context.buy_rate is None:
        #     return "Could you please provide the buy rate?"

        # If both are available, call API
        try:
            incentive = self.incentive_tool.run(self.context.dealer_name)
            # incentive = self.incentive_tool.run(self.context.contract_apr, self.context.buy_rate)
            result = f"The dealer incentive for the sale is ${incentive}.[final_answer]"
            
            # Reset context after final answer
            self.context.contract_apr = None
            self.context.buy_rate = None
            
            return result
        except Exception as e:
            return f"Sorry, I encountered an error while calculating the incentive: {str(e)}"

    def _extract_info_from_message(self, message: str) -> None:
        """Extract pricing-related information from the message"""
        super()._extract_info_from_message(message)
        
        message_lower = message.lower()

        print(f"Pricing Agent: _extract_info_from_message : Message is {message} ")
        # Extract dealer name if present - fixed pattern
        dealer_match = re.search(r'dealer(?:\s+name)?\s+(?:is|=|:)\s+([A-Za-z0-9\s]+)', message_lower)
        if dealer_match:
            # Clean up the dealer name (remove extra spaces, capitalize properly)
            dealer_name = dealer_match.group(1).strip()
            # Convert to title case (capitalize first letter of each word)
            dealer_name = ' '.join(word.capitalize() for word in dealer_name.split())
            self.context.dealer_name = dealer_name
            print(f"Dealer name extracted: {dealer_name}")
        else:
            print("No dealer name pattern matched in the message")

        # Extract APR information if present
        apr_match = re.search(r'(?:contract apr|apr|interest)(?:\s+is|\s*[:=])?\s*(\d+\.?\d*)', message_lower)
        if apr_match:
            self.context.contract_apr = float(apr_match.group(1))

        # Extract buy rate information if present
        buy_rate_match = re.search(r'(?:buy rate|buy|rate)(?:\s+is|\s*[:=])?\s*(\d+\.?\d*)', message_lower)
        if buy_rate_match and "apr" not in message_lower[buy_rate_match.start()-5:buy_rate_match.start()]:
            self.context.buy_rate = float(buy_rate_match.group(1))