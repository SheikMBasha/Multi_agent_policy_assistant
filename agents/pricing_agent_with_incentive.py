# """Pricing agent implementation for handling financial queries"""

# import re
# from typing import Dict, Any
# from agents.base_agent import SimplifiedAgent
# from context.conversation_context import ConversationContext
# from tools.calculateincentivetool import CalculateIncentiveTool

# class PricingAgent(SimplifiedAgent):
#     """Handles pricing related queries"""

#     def __init__(self, llm_config: Dict[str, Any], context: ConversationContext, incentive_tool: CalculateIncentiveTool):
#         super().__init__(
#             name="PricingAgent",
#             system_message="""
# You are the PricingAgent. You help calculate dealer incentives using contract APR and buy rate.

# Steps:
# 1. Ask the user for both contract APR and buy rate.
# 2. If one is missing, ask naturally like a human would.
# 3. Use previously provided values (shared context) if available.
# 4. Once both values are available, compute incentive as:
#    incentive = (contractAPR - buyRate) * 1000
# 5. Respond with the computed incentive clearly and end with [final_answer]

# Respond as naturally and conversationally as possible.
# """,
#             llm_config=llm_config,
#             context=context
#         )

#         self.incentive_tool = incentive_tool

#     def generate_response(self, message: str) -> str:
#         self._extract_info_from_message(message)

#         # Check what information is missing
#         if self.context.contract_apr is None:
#             return "Could you please provide the contract APR?"

#         if self.context.buy_rate is None:
#             return "Could you please provide the buy rate?"

#         # If both are available, call API
#         try:
#             incentive = self.incentive_tool.run(self.context.contract_apr, self.context.buy_rate)
#             result = f"The dealer incentive for the sale is ${incentive}.[final_answer]"
            
#             # Reset context after final answer
#             self.context.contract_apr = None
#             self.context.buy_rate = None
            
#             return result
#         except Exception as e:
#             return f"Sorry, I encountered an error while calculating the incentive: {str(e)}"

#     def _extract_info_from_message(self, message: str) -> None:
#         """Extract pricing-related information from the message"""
#         super()._extract_info_from_message(message)
        
#         message_lower = message.lower()

#         # Extract APR information if present
#         apr_match = re.search(r'(?:contract apr|apr|interest)(?:\s+is|\s*[:=])?\s*(\d+\.?\d*)', message_lower)
#         if apr_match:
#             self.context.contract_apr = float(apr_match.group(1))

#         # Extract buy rate information if present
#         buy_rate_match = re.search(r'(?:buy rate|buy|rate)(?:\s+is|\s*[:=])?\s*(\d+\.?\d*)', message_lower)
#         if buy_rate_match and "apr" not in message_lower[buy_rate_match.start()-5:buy_rate_match.start()]:
#             self.context.buy_rate = float(buy_rate_match.group(1))