from autogen import UserProxyAgent, GroupChat, GroupChatManager
from agents.router_agent import router_agent
from agents.pricing_agent import pricing_agent
from agents.policy_agent import policy_agent
from agents.dealer_agent import dealer_agent
from shared.llm_config import llm_config

user_proxy = UserProxyAgent(
    name="user",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=0,
    code_execution_config={"use_docker": False},  # 👈 This disables Docker usage
)

groupchat = GroupChat(
    agents=[
        user_proxy,
        router_agent,
        pricing_agent,
        policy_agent,
        dealer_agent
    ],
    messages=[],
    max_round=10,
)

manager = GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_config,
    code_execution_config={"use_docker": False}  # ✅ disables Docker here too
)


if __name__ == "__main__":
    print("🧠 Starting Multi-Agent Policy Assistant...")
    user_proxy.initiate_chat(manager, summary_method="last_n", summary_config={"last_n": 10})