from autogen import AssistantAgent
from shared.llm_config import llm_config
from shared.tools import log_complaint

dealer_agent = AssistantAgent(
    name="DealerAgent",
    llm_config=llm_config,
    system_message="""
You are the DealerAgent. Handle complaints about incentive payouts, application issues, or dealer account problems.

Log complaints and acknowledge with [final_answer] tag.
"""
)

@dealer_agent.register_for_execution()
def _(_, messages, **__):
    complaint = messages[-1]['content']
    log_complaint(complaint)
    return True, f"Thank you for reporting your concern. We have logged it and will escalate if necessary. [final_answer]"