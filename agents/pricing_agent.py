from autogen import AssistantAgent
from shared.llm_config import llm_config

pricing_agent = AssistantAgent(
    name="PricingAgent",
    llm_config=llm_config,
    system_message="""
You are the PricingAgent.

Your task is to calculate dealer incentives using the formula:
    incentive = (contractAPR - buyRate) * 1000

Instructions:
- Extract 'contractAPR' and 'buyRate' from the user message.
- If both are present, calculate the incentive and respond like:
  "The dealer incentive for this application is $<amount>. [final_answer]"
- If either is missing, ask the user politely to provide it.
- Format numbers clearly in the response.
"""
)
