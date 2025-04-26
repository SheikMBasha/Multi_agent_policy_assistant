from autogen import AssistantAgent
from shared.llm_config import llm_config
from shared.context import ConversationContext
from shared.schemas import DealerIncentiveRequest

pricing_agent = AssistantAgent(
    name="PricingAgent",
    llm_config=llm_config,
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
"""
)

@pricing_agent.register_for_execution()
def pricing_executor(_, messages, **__):
    from pydantic import ValidationError

    user_input = messages[-1]["content"]
    ConversationContext.update("last_user_input", user_input)

    current_context = ConversationContext.as_prompt()

    try:
        req = DealerIncentiveRequest(**ConversationContext.to_dict())
        result = calculate_dealer_compensation(req.dealer_name)
        ConversationContext.clear()
        return True, result
    except ValidationError:
        return True, f"""
We don't yet have all the information we need to calculate the dealer compensation.

{current_context}

Please ask the user for the missing value (dealer_name) in a friendly, conversational way.
Always end your response with [final_answer].
"""