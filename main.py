from autogen import UserProxyAgent, GroupChat, GroupChatManager
from agents.router_agent import router_agent
from agents.pricing_agent import pricing_agent
from agents.policy_agent import policy_agent
from agents.dealer_agent import dealer_agent
from shared.llm_config import llm_config
from shared.context import shared_context  # make sure you have this file

# 👋 Greet user and ask for name
print("👋 Hello! I'm your virtual assistant.")
name_input = input("May I know your name please? (e.g., Sheik or Ms. Raina): ")

# 👔 Prefix formatting
if name_input.strip().lower().startswith("ms"):
    user_name = f"Ms. {name_input.strip().split()[-1]}"
else:
    user_name = f"Mr. {name_input.strip().split()[-1]}"
shared_context.update("user_name", user_name)

print(f"Nice to meet you, {user_name}! How can I assist you today?\n")


# 🧠 Setup user proxy
user_proxy = UserProxyAgent(
    name="user",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=0,
    code_execution_config={"use_docker": False},  # 👈 This disables Docker usage
)

groupchat = GroupChat(
    agents=[
        user_proxy,  # keep user first if this is your current structure
        router_agent,
        pricing_agent,
        policy_agent,
        dealer_agent
    ],
    messages=[],
    max_round=20,
)

manager = GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_config,
    code_execution_config={"use_docker": False}  # ✅ disables Docker here too
)

if __name__ == "__main__":
    print("🧠 Starting Multi-Agent Policy Assistant...")
    user_proxy.initiate_chat(manager, summary_method="last_n", summary_config={"last_n": 10})
