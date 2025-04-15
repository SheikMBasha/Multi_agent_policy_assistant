from autogen import AssistantAgent
from shared.llm_config import llm_config

dealer_agent = AssistantAgent(
    name="DealerAgent",
    llm_config=llm_config,
    system_message="""
You are the DealerAgent. Always respond with the following message:

"Thank you for your request. We have created a ticket. Please be online while we transfer your call to our executive. [final_answer]"

Do not generate or vary your own response. Just return the message above exactly.
"""
)

@dealer_agent.register_for_execution()
def handle_dealer_request(_, messages, **__):
    return True, (
        "Thank you for your request. We have created a ticket. "
        "Please be online while we transfer your call to our executive. [final_answer]"
    )
