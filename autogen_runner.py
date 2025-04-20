from autogen import GroupChat, GroupChatManager, UserProxyAgent
from agents.router_agent import router_agent
from agents.pricing_agent import pricing_agent
from agents.policy_agent import policy_agent
from agents.dealer_agent import dealer_agent
from shared.llm_config import llm_config
from shared.context import shared_context

async def start_autogen_conversation(user_text: str) -> str:
    user_proxy = UserProxyAgent(
        name="user",
        human_input_mode="NEVER",
        code_execution_config={"use_docker": False}
    )

    groupchat = GroupChat(
        agents=[
            user_proxy,
            router_agent,
            pricing_agent,
            policy_agent,
            dealer_agent,
        ],
        messages=[],
        max_round=10
    )

    manager = GroupChatManager(
        groupchat=groupchat,
        llm_config=llm_config,
        code_execution_config={"use_docker": False}
    )

    await user_proxy.a_initiate_chat(manager, message=user_text)

    # Fetch last meaningful response (usually from the last speaker before user)
    for msg in reversed(groupchat.messages):
        if msg.get("content") and "[final_answer]" in msg["content"].lower():
            return msg["content"].replace("[final_answer]", "").strip()

    return "Sorry, I didn’t get that."

    # reply = user_proxy.initiate_chat(manager, message=user_text)
    # return reply.get("content", "Sorry, I didn’t get that.")

    # response = ""
    # for step in user_proxy.initiate_chat(manager, message=user_text):
    #     content = step.get("content", "")
    #     print("🔄 Intermediate:", content)
    #
    #     # ✅ Stop when final answer is reached
    #     if "[final_answer]" in content.lower():
    #         response = content.replace("[final_answer]", "").strip()
    #         break
    #
    # return response or "Sorry, I didn’t get that."
