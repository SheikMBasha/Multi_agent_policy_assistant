from autogen import AssistantAgent
from shared.llm_config import llm_config

router_agent = AssistantAgent(
    name="RouterAgent",
    llm_config=llm_config,
    system_message="""
You are the RouterAgent for a dealer voice assistant. Route the user's message to one of the following agents:

- @PricingAgent: If the user is asking about incentives or APR calculations
- @PolicyAgent: If the user asks about rules, policies, eligibility, or documentation
- @DealerAgent: If the user has a complaint or wants to log an issue

Always tag one agent and include the full user query.
"""
)