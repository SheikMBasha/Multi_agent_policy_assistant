from autogen import UserProxyAgent, GroupChat, GroupChatManager, initiate_swarm_chat
from shared.llm_config import llm_config
import os
import re

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
user_proxy = UserProxyAgent(
    name="user",
    human_input_mode="NEVER",
    is_termination_msg=lambda msg: not msg.get("content") or msg.get("content", "") == "" ,
    code_execution_config=code_execution_config,
    max_consecutive_auto_reply=10
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
    name="calculate_dealer_compensation",
    description="Calculate dealer incentive based on contract APR and buy rate."
)
def calculate_dealer_compensation(dealer_name: str) -> str:
    try:
        url = "http://localhost:8000/calculate-compensation"  # Replace with your deployed URL if needed
        params = {"dealerName": dealer_name}
        response = requests.get(url, params=params)

        if response.status_code == 200:
            compensation = response.json().get("compensation", None)
            return f"The calculated dealer compensation is ${compensation}. [final_answer]"
        else:
            return "Failed to fetch compensation from the API. [final_answer]"
    except Exception as e:
        return f"Error occurred: {str(e)}"



user_proxy.description="Gets the user's input and forwards it to the group chat. It is the agent which will return the final answer."
pricing_agent.description="Calculates the dealer compensation based on dealer name. It is the agent which will return the final answer."
dealer_agent.description="Handles complaints and issues raised by car dealers. It acknowledges the problem, confirms a ticket has been created, and transfers the user to a human executive. It is the agent which will return the final answer."
policy_agent.description="Handles policy-related queries and provides information about the bank's policies. Use if the user is asking about loan policies, rules, required documents, eligibility, term length, maximum age, conditions, or approval criteria. It is the agent which will return the final answer."
small_talk_agent.description="Engages users in friendly, natural conversation. It greets the user, asks for their name, and ends the conversation politely."
code_interpreter.description="Executes code and provides the results. It can also set and get the user's name."

allowed_transitions = {
    user_proxy: [pricing_agent, dealer_agent, policy_agent, small_talk_agent],
    pricing_agent: [user_proxy, code_interpreter],
    dealer_agent: [user_proxy],
    policy_agent: [user_proxy],
    small_talk_agent: [user_proxy, code_interpreter],
    code_interpreter: [pricing_agent, small_talk_agent, user_proxy],
}

# Create the group chat
groupchat = GroupChat(
    agents=[
        user_proxy,
        pricing_agent,
        policy_agent,
        dealer_agent,
        small_talk_agent,
        code_interpreter
    ],
    messages=[],
    max_round=20,
    send_introductions=True,
    # allowed_or_disallowed_speaker_transitions=allowed_transitions,
    # speaker_transitions_type="allowed",
)

# Create the group chat manager
manager = GroupChatManager(
    groupchat=groupchat,
    llm_config=llm_config,
    code_execution_config=code_execution_config
)


def process_pricing_agent(user_input):

    dealer_name_match = re.search(r"dealer name is ([\w\s]+)", user_input, re.IGNORECASE)

    messages = [{"role": "user", "content": user_input}]
    response = pricing_agent.generate_reply(messages=messages)
    print(f"Agent response: {response}")


    if isinstance(response, str):
        return response
    
    if not dealer_name_match:
        return "Please provide the dealer name to calculate the compensation."
    
    
    if response and response.get("tool_calls"):
        tool_messages = []

        for tool_call in response["tool_calls"]:
            import json
            function_name = tool_call["function"]["name"]
            function_args = tool_call["function"]["arguments"]
            args = json.loads(function_args)
            dealerName = args.get("dealer_name")
            tool_call_id = tool_call["id"]

            if function_name == "calculate_dealer_compensation":
                result = calculate_dealer_compensation(dealerName)
                tool_content = result
                print(f"Tool call result: {tool_content}")

            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_content
            })
        
        messages.append({"role": "assistant", "content": None, "tool_calls": response["tool_calls"]})
        messages.extend(tool_messages)
        
        # Step 5: Now generate final agent reply with the updated message history
        final_response = pricing_agent.generate_reply(messages=messages)
        print(f"Final response: {final_response}")
        return final_response

                
    
    return response.content


def process_small_talk(user_input):
    # Step 1: Start with the user message
    messages = [{"role": "user", "content": user_input}]
    
    # Step 2: Get the agent's first reply
    response = small_talk_agent.generate_reply(messages=messages)
    print(f"Agent response: {response}")

    if isinstance(response, str):
        return response
    
    # Step 3: If agent made tool_calls, handle them
    if response and response.get("tool_calls"):
        tool_messages = []
        
        for tool_call in response["tool_calls"]:
            function_name = tool_call["function"]["name"]
            function_args = tool_call["function"]["arguments"]
            tool_call_id = tool_call["id"]

            if function_name == "get_current_user_name":
                result = get_current_user_name()
                tool_content = f"The current user name is: {result}"
                print(f"Tool call result: {tool_content}")

            elif function_name == "set_current_user_name":
                import json
                args = json.loads(function_args)
                name = args.get("name")
                set_current_user_name(name)
                tool_content = f"User name has been set to {name}."

            else:
                tool_content = "Function not implemented."

            # VERY IMPORTANT: Append a 'tool' message for each tool call
            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_content
            })
        
        # Step 4: Add the assistant tool_call and the tool messages to message history
        messages.append({"role": "assistant", "content": None, "tool_calls": response["tool_calls"]})
        messages.extend(tool_messages)
        
        # Step 5: Now generate final agent reply with the updated message history
        final_response = small_talk_agent.generate_reply(messages=messages)
        print(f"Final response: {final_response}")
        return final_response

    # Step 6: If no tool calls, just return the agent's normal response
    if response and response.get("content"):
        return response["content"]



def process_user_query(user_input):
    # Step 1: Send user input to moderator for routing
    moderator_response = router_agent.generate_reply(
        messages=[{"role": "user", "content": user_input}]
    )
    print(f"Moderator: {moderator_response}")
    
    # Step 2: Based on moderator's decision, route to appropriate agent
    if "pricingagent" in moderator_response.lower():
        return process_pricing_agent(user_input)
    
    elif "policyagent" in moderator_response.lower():
        final_response = policy_agent.generate_reply(
            messages=[{"role": "user", "content": user_input}]
        )
        print(f"Policy Agent: {final_response}")
        return final_response
    
    elif "dealeragent" in moderator_response.lower():
        final_response = dealer_agent.generate_reply(
            messages=[{"role": "user", "content": user_input}]
        )
        print(f"Dealer Agent: {final_response}")
        return final_response
    
    elif "smalltalkagent" in moderator_response.lower():
        return process_small_talk(user_input)
    
    else:
        # Default fallback if moderator doesn't make a clear decision
        default_response = "I'm not sure which agent can best help you. Could you rephrase your question?"
        print(f"System: {default_response}")
        return default_response


allowed_agents = {"PolicyAgent", "PricingAgent", "DealerAgent", "SmallTalkAgent", "code-interpreter"}

def chat_with_agents(user_input: str) -> str:
    print("User input received:", user_input)

    #Start the conversation
    # response = user_proxy.initiate_chat(
    #     recipient=manager,
    #     message=user_input,
    #     summary_method="reflection_with_llm",
    #     summary_config={"last_n": 10},
    # )

    # print("Conversation so far:")
    # for message in groupchat.messages:
    #     print(f"messages:{message}")

    # # Find the last message with [final_answer]
    # for msg in reversed(groupchat.messages):
    #     if msg.get("name") in allowed_agents and "[final_answer]" in msg.get("content", "").lower():
    #         # Return the message without the [final_answer] part for cleaner output
    #         return msg["content"].replace("[final_answer]", "").strip()

    # # Only if no termination message was found
    # return "Sorry, I didn't get that. Can you please repeat?"
    return process_user_query(user_input)