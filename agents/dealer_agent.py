from autogen import AssistantAgent
from shared.llm_config import llm_config

dealer_agent = AssistantAgent(
    name="DealerAgent",
    llm_config=llm_config,
    system_message="""
You are the DealerAgent.

Your job is to handle complaints and issues raised by car dealers. If the user reports a missing payment, issue with an application, or any service delay:

1. Acknowledge the problem
2. Confirm a ticket has been created
3. Politely mention that you're transferring them to a human executive
4. End every response with: [final_answer]

Example:
"Thank you for your request. We have created a ticket. Please be online while we transfer your call to our executive. [final_answer]"
"""
)



# from autogen import AssistantAgent
# from shared.llm_config import llm_config
# from shared.tools import log_complaint
#
# dealer_agent = AssistantAgent(
#     name="DealerAgent",
#     llm_config=llm_config,
#     system_message="""
# You are the DealerAgent. Handle complaints about incentive payouts, application issues, or dealer account problems.
#
# Log complaints and acknowledge with [final_answer] tag.
# """
# )
#
# @dealer_agent.register_for_execution()
# def _(_, messages, **__):
#     complaint = messages[-1]['content']
#     log_complaint(complaint)
#     return True, f"Thank you for reporting your concern. We have logged it and will escalate if necessary. [final_answer]"