# # email_reader_agent.py
# from autogen import AssistantAgent
# from shared import llm_config
#
# EmailReaderAgent = AssistantAgent(
#     name="EmailReaderAgent",
#     llm_config=llm_config,
#     system_message=("You are an AI assistant that processes emails to generate structured Jira ticket content.\n"
#                     "Extract the following fields from the email:\n"
#                     "1. Summary (title of the issue)\n"
#                     "2. Description (detailed explanation)\n"
#                     "3. Priority (High, Medium, Low)\n"
#                     "4. Tags (comma-separated keywords)\n"
#                     "If information is missing, infer based on context or leave it blank.\n\n"
#                     "ALWAYS format your response as:\n"
#                     "```jira\n"
#                     "Summary: [extracted summary]\n"
#                     "Description: [extracted description]\n"
#                     "Priority: [extracted priority]\n"
#                     "Tags: [extracted tags]\n"
#                     "```"),
#     code_execution_config=False
# )