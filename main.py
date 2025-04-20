from autogen import UserProxyAgent, GroupChat, GroupChatManager
from shared.llm_config import llm_config
import os

# Import agents
from agents.router_agent import router_agent
from agents.policy_agent import policy_agent
from agents.pricing_agent import pricing_agent
from agents.dealer_agent import dealer_agent
from agents.smallTalk_agent import small_talk_agent
from typing import Annotated
import requests


current_user_name = "Unknown"

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
    human_input_mode="NEVER",
    is_termination_msg=lambda msg: "[final_answer]" in msg.get("content", "").lower(),
    code_execution_config=code_execution_config,
    max_consecutive_auto_reply=0
)

code_interpreter = UserProxyAgent(
    "code-interpreter",
    human_input_mode="NEVER",
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    default_auto_reply="",
    is_termination_msg=lambda x: x.get("content", "").find("TERMINATE") >= 0,
)


@code_interpreter.register_for_execution()
@small_talk_agent.register_for_llm(
    name="get_current_user_name",
    description="Get the current user's name."
)
def get_current_user_name() -> str:
    """Returns the current user's name."""
    global current_user_name
    print("Fetching current user name...")
    return current_user_name


@code_interpreter.register_for_execution()
@small_talk_agent.register_for_llm(
    name="set_current_user_name",
    description="Set the current user's name with optional title (Mr/Ms)."
)
def set_current_user_name(
    name: Annotated[str, "User's name"],
    title: Annotated[str, "Optional title (Mr/Ms)"] = None
) -> str:
    """Sets the current user's name and returns confirmation message."""
    global current_user_name
    if title:
        current_user_name = f"{title}. {name}"
    else:
        current_user_name = name
    return f"Name has been set to: {current_user_name}"


# @router_agent.register_for_llm(
#     name="get_current_user_name",
#     description="Get the current user's name."
# )
# def get_current_user_name() -> str:
#     """Returns the current user's name."""
#     global current_user_name
#     print("Fetching current user name...")
#     return current_user_name

@code_interpreter.register_for_execution()
@pricing_agent.register_for_llm(
    name="calculate_dealer_incentive",
    description="Calculate dealer incentive based on contract APR and buy rate."
)
def calculate_dealer_incentive(contractAPR: float, buyRate: float) -> str:
    try:
        url = "http://localhost:8000/calculate-incentive"  # Replace with your deployed URL if needed
        params = {"contractAPR": contractAPR, "buyRate": buyRate}
        response = requests.get(url, params=params)

        if response.status_code == 200:
            incentive = response.json().get("incentive", None)
            return f"The calculated dealer incentive is ${incentive}."
        else:
            return "Failed to fetch incentive from the API."
    except Exception as e:
        return f"Error occurred: {str(e)}"


# def main():
#     print("👋 Hello! I'm your virtual assistant.")
#     name_input = input("May I know your name please? (e.g., Srikanth or Ms. Raina): ")

#     # Format the name
#     if name_input.lower().startswith("ms"):
#         user_name = f"Ms. {name_input.split()[-1]}"
#     else:
#         user_name = f"Mr. {name_input.split()[-1]}"

#     print(f"Nice to meet you, {user_name}! How can I assist you today?\n")
#     print("🧠 Starting Multi-Agent Policy Assistant...")

#     while True:
#         user_text = input("> ")
#         if user_text.lower() in ["exit", "quit", "bye"]:
#             print("Thank you for using our service. Have a great day!")
#             break

#         # Start chat
#         user_proxy.initiate_chat(
#             manager,
#             message=user_text
#         )
#         print("\n")  # Add a blank line after each conversation


# if __name__ == "__main__":
#     main()

# Create the group chat
groupchat = GroupChat(
    agents=[
        user_proxy,
        router_agent,
        pricing_agent,
        policy_agent,
        dealer_agent,
        small_talk_agent,
        code_interpreter
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


allowed_agents = {"PolicyAgent", "PricingAgent", "DealerAgent", "SmallTalkAgent"}

def chat_with_agents(user_input: str) -> str:
    print("User input received:", user_input)

    # Start the conversation
    response = user_proxy.initiate_chat(
        recipient=manager,
        message=user_input,
        summary_method="last_n",
        summary_config={"last_n": 10},
    )

    print("Conversation so far:")
    for message in groupchat.messages:
        print(f"messages:{message}")

    # Reverse loop to find last relevant message from allowed agents
    for msg in reversed(groupchat.messages):
        if msg.get("name") in allowed_agents:
            return msg["content"]

    return "Sorry, i didn't get that. Can you please repeat?"