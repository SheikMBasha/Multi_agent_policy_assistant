from typing import Dict, Any, Optional
#!/usr/bin/env python3
# simplified_main.py - Main orchestration script for automotive voice assistant

import os
import sys
import signal
import argparse
from uuid import uuid4
import time
from datetime import datetime

from config.llm_config import get_llm_config
from config.system_config import get_system_config

# Import from simplified_agents instead of context
from simplified_agents import ConversationContext, create_simplified_agents
from tools.calculateincentivetool import CalculateIncentiveTool


# Global context for signal handlers
global_context = None

def signal_handler(sig, frame):
    """Handle interrupt signals by exiting gracefully"""
    print("\n\nReceived interrupt signal. Ending conversation...")
    print("Thank you for using our Automotive Assistant. Goodbye!")
    sys.exit(0)

def setup_signal_handlers():
    """Setup signal handlers for graceful exit"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Automotive Multi-Agent assistant system")
    parser.add_argument("--user-id", type=str, help="User Id for persistent profiles")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--log-file", type=str, help="Path to log file")
    return parser.parse_args()

def log_interaction(log_file, user_message, agent_name, agent_response):
    """Log interactions to a file if specified"""
    if not log_file:
        return
    
    try:
        with open(log_file, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] USER: {user_message}\n")
            f.write(f"[{timestamp}] {agent_name}: {agent_response}\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

def initialize_system(args):
    """Initialize all system components"""
    print("Initializing Automotive Assistant Multi-Agent System...")

    # Set up context
    context = ConversationContext()
    global global_context
    global_context = context

    # Generate a session Id
    session_id = args.user_id if args.user_id else f"session_{uuid4().hex[:8]}"

    # Get LLM configuration
    try:
        llm_config = get_llm_config()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set your OpenAI key")
        sys.exit(1)

    system_config = get_system_config()

    #create the tools
    incentive_tool = CalculateIncentiveTool(api_url="http://localhost:8000/calculate-incentive")

    # Create simplified agents with context
    agents = create_simplified_agents(llm_config, context, incentive_tool)

    return context, agents, system_config

def run_conversation(context, agents, system_config, args):
    """Run the main conversation loop"""
    conversation_settings = system_config["conversation"]

    print("\n=== Automotive Assistant System ===")
    print("Type your questions about our vehicles, pricing, policies, or dealerships,")
    print("(Type 'exit' to end the conversation)")

    # Start with SmallTalkAgent greeting
    greeting = conversation_settings["greeting_message"]
    print(f"\nSmallTalkAgent: {greeting}")
    context.conversation_started = True

    # Track if the conversation should continue
    active = True

    # Track the timeout
    last_interaction_time = time.time()
    timeout_seconds = conversation_settings.get("timeout_seconds", 300)

    # Main conversation loop
    last_questioning_agent = None  # To keep track of the last agent asking a question

    while active:
        # Check for timeout
        current_time = time.time()
        if (current_time - last_interaction_time) > timeout_seconds:
            print("\nIt seems like you've been inactive for a while. Would you like to continue? (yes/no)")
            response = input("\nYou: ").lower()
            if response != "yes" and response != "y":
                active = False
                break
            last_interaction_time = current_time

        # Get user input
        try:
            user_message = input("\nYou: ")
            last_interaction_time = time.time()
        except EOFError:
            break

        # Handle exit commands
        if user_message.lower() in ['exit', 'quit', 'bye', 'goodbye']:
            farewell = conversation_settings["farewell_message"]
            print(f"\nSmallTalkAgent: {farewell}")
            context.add_to_history("SmallTalkAgent", farewell)
            active = False
            break

        # Handle thanks message
        if any(thank_you_phrase in user_message.lower() for thank_you_phrase in ["thank you", "thanks", "thanks a lot", "thank you very much"]):
            thanks_response = "You're very welcome! Is there anything else I can assist you with?"
            print(f"\nSmallTalkAgent: {thanks_response}")
            context.add_to_history("SmallTalkAgent", thanks_response)
            continue

        # Add to history
        context.add_to_history("User", user_message)

        # Special handling for getting the user's name
        if not context.user_name:
            name = context.extract_name(user_message)
            if name:
                context.user_name = name
                response = f"Nice to meet you, {name}! How can I help you with your automotive needs today?"
                print(f"\nSmallTalkAgent: {response}")
                context.add_to_history("SmallTalkAgent", response)
                continue
            else:
                response = "I didn't catch your name. Could you please tell me your name?"
                print(f"\nSmallTalkAgent: {response}")
                context.add_to_history("SmallTalkAgent", response)
                continue

        # Ask the moderator to determine which agent should handle this
        selected_agent_name = agents["moderator"].determine_agent(user_message)

        # If the last agent asked a question, route the question back to the same agent
        if last_questioning_agent and last_questioning_agent != selected_agent_name:
            selected_agent_name = last_questioning_agent

        # Display debug info if requested
        if args.debug:
            print(f"\nDEBUG - Moderator selected: {selected_agent_name}")
        
        # Track the selected agent in context
        context.last_active_agent = selected_agent_name
        
        # Convert display name to internal key
        agent_mapping = {
            "PricingAgent": "pricing",
            "PolicyAgent": "policy", 
            "DealerAgent": "dealer",
            "SmallTalkAgent": "smalltalk"
        }
        agent_key = agent_mapping.get(selected_agent_name, "smalltalk")
        
        # Get the response from the selected agent
        response = agents[agent_key].generate_response(user_message)

        # If the response is a question, update last_questioning_agent
        if "?" in response:
            last_questioning_agent = selected_agent_name

        # Display the response to the user
        print(f"\n{selected_agent_name}: {response}")

        # Check if the response contains [final_answer] to identify it as the final response
        if "[final_answer]" in response:
            # No follow-up prompt here, just identify final answer
            context.add_to_history(selected_agent_name, response)

        # Log the interaction
        log_interaction(args.log_file, user_message, selected_agent_name, response)





def main():
    """Main function to run the automotive agent system"""
    # Set up signal handlers for graceful exit
    setup_signal_handlers()

    # Parse command line arguments
    args = parse_arguments()

    try:
        # Initialize the system
        context, agents, system_config = initialize_system(args)

        # Run the conversation
        run_conversation(context, agents, system_config, args)

        print("\nThank you for using our Automotive Assistant. Goodbye!")

    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())