from autogen import AssistantAgent
from shared.llm_config import llm_config
from shared.context import ConversationContext
from shared.schemas import DealerIncentiveRequest

# def calculate_dealer_incentive(contractAPR: float, buyRate: float) -> str:
#     try:
#         url = "http://localhost:8000/calculate-incentive"  # Replace with your deployed URL if needed
#         params = {"contractAPR": contractAPR, "buyRate": buyRate}
#         response = requests.get(url, params=params)

#         if response.status_code == 200:
#             incentive = response.json().get("incentive", None)
#             return f"The calculated dealer incentive is ${incentive}."
#         else:
#             return "Failed to fetch incentive from the API."
#     except Exception as e:
#         return f"Error occurred: {str(e)}"



pricing_agent = AssistantAgent(
    name="PricingAgent",
    llm_config=llm_config,
    system_message="""
You are the PricingAgent. You assist users in calculating dealer incentives using the formula:

You have access to a function named `calculate_dealer_incentive(contractAPR: float, buyRate: float)` which performs the calculation and returns the result.

Behavior Instructions:
1. Always start by asking the user for both the contract APR and buy rate, if not already provided.
2. If the user provides only one value, acknowledge it and ask for the missing one.
3. Once you have both `contractAPR` and `buyRate`, call the tool `calculate_dealer_incentive(contractAPR, buyRate)`.
4. After receiving the result, reply with a clear, friendly message showing the incentive value and end your message with `[final_answer]`.
5. Keep the tone natural and conversational, like you're helping a colleague.
6. Remember values from earlier in the conversation unless the user updates them.

Only call the tool once both values are available. If any are missing, ask for them.
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
        result = calculate_dealer_incentive(req.contractAPR, req.buyRate)
        ConversationContext.clear()
        return True, result
    except ValidationError:
        return True, f"""
We don't yet have all the information we need to calculate the dealer incentive.

{current_context}

Please ask the user for the missing values (contract APR or buy rate) in a friendly, human way.
"""

