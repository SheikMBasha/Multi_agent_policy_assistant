from autogen import AssistantAgent
from shared.llm_config import llm_config
from shared.context import ConversationContext
from shared.schemas import DealerIncentiveRequest

pricing_agent = AssistantAgent(
    name="PricingAgent",
    llm_config=llm_config,
    system_message="""
You are the PricingAgent. You help calculate dealer incentives using contract APR and buy rate.

Steps:
1. Ask the user for both contract APR and buy rate.
2. If one is missing, ask naturally like a human would.
3. Use previously provided values (shared context) if available.
4. Once both values are available, compute incentive as:
   incentive = (contractAPR - buyRate) * 1000
5. Respond with the computed incentive clearly and end with [final_answer]

Respond as naturally and conversationally as possible.
"""
)

@pricing_agent.register_for_execution()
def pricing_executor(_, messages, **__):
    from pydantic import ValidationError
    user_input = messages[-1]["content"]

    # update context from LLM-extracted values
    ConversationContext.update("last_user_input", user_input)

    # assemble the prompt for LLM
    current_context = ConversationContext.as_prompt()

    try:
        req = DealerIncentiveRequest(**ConversationContext.to_dict())
        incentive = (req.contractAPR - req.buyRate) * 1000
        ConversationContext.clear()
        return True, f"Great! The dealer incentive is estimated to be ${incentive:.2f}. [final_answer]"
    except ValidationError:
        # Let the LLM naturally handle missing values in the prompt
        return True, f"""
Use the following partial information provided so far:
{current_context}

Now, naturally ask the user to provide the missing information (contract APR or buy rate) in a human way.
"""
