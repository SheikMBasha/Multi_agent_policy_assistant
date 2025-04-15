from autogen import UserProxyAgent, GroupChat, GroupChatManager
from shared.llm_config import llm_config
import os

# Import agents
from agents.router_agent import router_agent
from agents.policy_agent import policy_agent
from agents.pricing_agent import pricing_agent
from agents.dealer_agent import dealer_agent


# Custom UserProxyAgent implementation
class CustomUserProxyAgent(UserProxyAgent):
    def __init__(self, name, **kwargs):
        super().__init__(name=name, **kwargs)

    def get_human_input(self, prompt=None):
        """Completely override the prompt"""
        return input("> ")

    def receive(self, message, sender, request_reply=None, silent=False):
        """Override to control reply behavior"""
        self.chat_messages[sender].append(message)
        if request_reply is False or silent:
            return None
        if "[final_answer]" in message.get("content", "").lower():
            print("\n")  # Add a blank line after final answer
            return self.generate_reply(self.chat_messages[sender], sender)
        return None


# Configure code execution - explicitly disable Docker
code_execution_config = {
    "use_docker": False,
    "last_n_messages": 2,
    "work_dir": "coding",
    "timeout": 60
}

# Create user proxy agent using custom implementation
user_proxy = CustomUserProxyAgent(
    name="user",
    human_input_mode="TERMINATE",
    is_termination_msg=lambda msg: "[final_answer]" in msg.get("content", "").lower(),
    code_execution_config=code_execution_config,
    max_consecutive_auto_reply=0
)

# Create the group chat
groupchat = GroupChat(
    agents=[
        user_proxy,
        router_agent,
        pricing_agent,
        policy_agent,
        dealer_agent
    ],
    messages=[],
    max_round=20,
)

# Create the group chat manager
manager = GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_config,
    code_execution_config=code_execution_config
)


def main():
    print("👋 Hello! I'm your virtual assistant.")
    name_input = input("May I know your name please? (e.g., Srikanth or Ms. Raina): ")

    # Format the name
    if name_input.lower().startswith("ms"):
        user_name = f"Ms. {name_input.split()[-1]}"
    else:
        user_name = f"Mr. {name_input.split()[-1]}"

    print(f"Nice to meet you, {user_name}! How can I assist you today?\n")
    print("🧠 Starting Multi-Agent Policy Assistant...")

    while True:
        user_text = input("> ")
        if user_text.lower() in ["exit", "quit", "bye"]:
            print("Thank you for using our service. Have a great day!")
            break

        # Start chat
        user_proxy.initiate_chat(
            manager,
            message=user_text
        )
        print("\n")  # Add a blank line after each conversation


if __name__ == "__main__":
    main()