"""Agents module for the voice assistant"""

from typing import Dict, Any
from context.conversation_context import ConversationContext
from tools.calculateincentivetool import CalculateIncentiveTool

from agents.moderator_agent import ModeratorAgent
from agents.pricing_agent import PricingAgent
from agents.policy_agent import PolicyAgent
from agents.dealer_agent import DealerAgent
from agents.smalltalk_agent import SmallTalkAgent

def create_agents(llm_config: Dict[str, Any], context: ConversationContext, incentive_tool: CalculateIncentiveTool):
    """Create all simplified agents"""
    return {
        "moderator": ModeratorAgent(llm_config, context),
        "pricing": PricingAgent(llm_config, context, incentive_tool),
        "policy": PolicyAgent(llm_config, context),
        "dealer": DealerAgent(llm_config, context),
        "smalltalk": SmallTalkAgent(llm_config, context)
    }