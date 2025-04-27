# api_server.py
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time
import os
import re
from twilio.twiml.voice_response import VoiceResponse, Gather

# Import your agent system
from config.llm_config import get_llm_config
from config.system_config import get_system_config
from context.conversation_context import ConversationContext
from agents import create_agents
from tools.calculateincentivetool import CalculateIncentiveTool

# Session management for phone calls
phone_sessions = {}

# Initialize your agent system
context = ConversationContext()
llm_config = get_llm_config()
system_config = get_system_config()
incentive_tool = CalculateIncentiveTool(api_url="http://localhost:8000/calculate-compensation")
agents = create_agents(llm_config, context, incentive_tool)

app = FastAPI(title="Automotive Assistant API")

class MessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    user_name: Optional[str] = None
    debug_cache: Optional[bool] = False

class MessageResponse(BaseModel):
    agent: str
    response: str
    context: Dict[str, Any] = {}
    response_time_ms: float
    cache_hit: Optional[bool] = None

# Utility function to process messages (used by both chat API and voice)
def process_message(user_message, session_id="default", user_name=None):
    # Start the timer
    start_time = time.time()
    print("Begin Process_message")
    
    # Get or create session context
    if session_id != "default" and session_id in phone_sessions:
        # Use the phone session if it exists
        context = phone_sessions[session_id]
        print(f"Using existing phone session: {session_id}")
    else:
        # Using the global context if not a phone session
        context = globals()["context"]
        print(f"Using global context for session: {session_id}")
    
    try:
        # Set user name if provided
        if user_name and not context.user_name:
            context.user_name = user_name
            print(f"Set user name to: {user_name}")
        
        # Add to history
        context.add_to_history("User", user_message)
        
        # Special handling for getting the user's name
        if not context.user_name:
            name = context.extract_name(user_message)
            if name:
                context.user_name = name
                response = f"Hello {name}! I'm here to help. How can I assist you today?"
                # Calculate elapsed time in milliseconds
                elapsed_time_ms = (time.time() - start_time) * 1000
                return {
                    "agent": "SmallTalkAgent", 
                    "response": response, 
                    "context": {"user_name": name},
                    "response_time_ms": elapsed_time_ms,
                    "cache_hit": False
                }
            else:
                response = "I didn't catch your name. Could you please tell me your name?"
                # Calculate elapsed time in milliseconds
                elapsed_time_ms = (time.time() - start_time) * 1000
                return {
                    "agent": "SmallTalkAgent", 
                    "response": response, 
                    "context": {},
                    "response_time_ms": elapsed_time_ms,
                    "cache_hit": False
                }
        
        # Handle thanks message
        if any(thank_you in user_message.lower() for thank_you in ["thank you", "thanks"]):
            response = f"You're very welcome, {context.user_name}! Is there anything else I can assist you with?"
            # Calculate elapsed time in milliseconds
            elapsed_time_ms = (time.time() - start_time) * 1000
            return {
                "agent": "SmallTalkAgent", 
                "response": response, 
                "context": {"user_name": context.user_name},
                "response_time_ms": elapsed_time_ms,
                "cache_hit": False
            }
        
        # Ask the moderator to determine which agent should handle this
        selected_agent_name = agents["moderator"].determine_agent(user_message)
        print(f"Selected agent is {selected_agent_name}")
        
        # Convert display name to internal key
        agent_mapping = {
            "PricingAgent": "pricing",
            "PolicyAgent": "policy", 
            "DealerAgent": "dealer",
            "SmallTalkAgent": "smalltalk"
        }
        agent_key = agent_mapping.get(selected_agent_name, "smalltalk")
        print(f"Agent key is {agent_key}")

        # Check for goodbye intent to handle specially
        goodbye_phrases = ["thank you", "thanks", "goodbye", "bye", "i'm good", "i think i'm good", "that's all", "no i'm good"]
        is_goodbye = any(phrase in user_message.lower() for phrase in goodbye_phrases)
    
        if is_goodbye:
            # Handle goodbye specially
            goodbye_response = f"Thank you for your time, {context.user_name if context.user_name else 'there'}! Have a great day. Goodbye!"
            return {
                "agent": "SmallTalkAgent",
                "response": goodbye_response,
                "context": {"user_name": context.user_name},
                "response_time_ms": (time.time() - start_time) * 1000,
                "cache_hit": False
            }
    
        
        # Get the response from the selected agent
        response = agents[agent_key].generate_response(user_message)
        print(f"selected agent response is {response}")
        
        # # If this is a policy response and we have a name, ensure it's personalized
        # if selected_agent_name == "PolicyAgent" and context.user_name:
        #     # Check if the response starts with a generic greeting
        #     if not any(f"{context.user_name}" in response.split()[:10]):
        #         # If the user's name isn't mentioned in first few words, personalize it
        #         if response.startswith("The policy"):
        #             response = f"{context.user_name}, {response[0].lower() + response[1:]}"
                
        # Return response with context info
        context_info = {
            "user_name": context.user_name,
            "turns_count": context.turns_count
        }
        
        # Calculate elapsed time in milliseconds
        elapsed_time_ms = (time.time() - start_time) * 1000
        print(f"Elapsed time is {elapsed_time_ms}")
        return {
            "agent": selected_agent_name,
            "response": response,
            "context": context_info,
            "response_time_ms": elapsed_time_ms,
            "cache_hit": False  # Default to False, you can implement actual cache detection
        }
        
    except Exception as e:
        # Calculate elapsed time even for errors
        elapsed_time_ms = (time.time() - start_time) * 1000
        error_msg = f"Error ({elapsed_time_ms:.2f}ms): {str(e)}"
        print(error_msg)
        return {
            "agent": "System",
            "response": f"I'm sorry, but I encountered an error: {str(e)}",
            "context": {},
            "response_time_ms": elapsed_time_ms,
            "cache_hit": False
        }

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    # Process the message with the utility function
    result = process_message(request.message, request.session_id, request.user_name)
    return result

@app.post("/voice", response_class=PlainTextResponse)
async def voice(request: Request):
    form = await request.form()
    user_input = form.get("SpeechResult")
    call_sid = form.get("CallSid", "unknown")
    
    # Create a unique session ID for this call
    session_id = f"call_{call_sid}"
    
    # Create or get session context for this call
    if session_id not in phone_sessions:
        phone_sessions[session_id] = ConversationContext()
        # Initialize metadata for tracking entity recognition failures
        phone_sessions[session_id].metadata = {"entity_failures": 0}
        print(f"Created new phone session: {session_id}")
    
    response = VoiceResponse()

    if user_input:
        print(f"User said: {user_input}")
        
        # Get context for this session
        context = phone_sessions[session_id]
        
        # Check for goodbye intent first
        goodbye_phrases = ["thank you", "thanks", "goodbye", "bye", "i'm good", "i think i'm good", "that's all", "no i'm good"]
        is_goodbye = any(phrase in user_input.lower() for phrase in goodbye_phrases)
        
        if is_goodbye:
            # Handle goodbye directly
            farewell_message = f"Thank you for calling, {context.user_name if hasattr(context, 'user_name') and context.user_name else ''}. Have a great day!"
            response.say(farewell_message)
            response.hangup()
            # Clean up the session
            if session_id in phone_sessions:
                del phone_sessions[session_id]
                print(f"Deleted phone session: {session_id}")
            return str(response)
        
        # Preprocess user input for better entity recognition
        processed_input = user_input
        
        # Normalize dealer name mentions
        dealer_patterns = [
            (r'\b(?:the|at|from)\s+([A-Za-z]+(?:\s+Motors|\s+Dealership|\s+Auto|\s+Cars)?)\b', r'dealer is \1'),
            (r'\b([A-Za-z]+(?:\s+Motors|\s+Dealership|\s+Auto|\s+Cars))\b', r'dealer is \1')
        ]
        
        for pattern, replacement in dealer_patterns:
            if re.search(pattern, processed_input, re.IGNORECASE):
                processed_input = re.sub(pattern, replacement, processed_input, flags=re.IGNORECASE)
                print(f"Normalized dealer input: {processed_input}")
        
        # Get the agent's response using our central processing function
        try:
            print("Begin Process_message")
            result = process_message(processed_input, session_id)
            
            # Verify result is a dictionary
            if isinstance(result, str):
                print(f"WARNING: process_message returned a string instead of a dict: {result}")
                agent_reply = result
            else:
                agent_reply = result.get("response", "I'm sorry, I'm having trouble processing that request.")
        except Exception as e:
            print(f"Error in process_message: {e}")
            agent_reply = f"I'm sorry, but I'm having trouble understanding. Can I help you with something else?"
        
        # Clean the tags for speaking
        bot_reply = agent_reply.replace("[final_answer]", "").replace("[user_input_needed]", "").strip()
        print(f"Bot says: {bot_reply}")
        
        # Say the bot's response
        response.say(bot_reply)
        
        # Check for repeated entity recognition failures
        is_asking_for_dealer = "dealer name" in bot_reply.lower() or "dealership" in bot_reply.lower()
        if is_asking_for_dealer and context.metadata["entity_failures"] >= 2:
            # Switch to guided approach after multiple failures
            response.pause(length=1)
            response.say("I'm having trouble understanding the dealer name. Let me offer some options.")
            
            gather = Gather(
                input="speech",
                timeout=8,
                speech_timeout="auto",
                action="/voice",
                method="POST",
                hints="Tesla, Ford, Toyota, Honda, BMW, Mercedes, Chevrolet",
                speech_model="phone_call",
                language="en-US en-IN"
            )
            
            gather.say("Please say one of these dealers: Tesla, Ford, Toyota, Honda, BMW, Mercedes, or Chevrolet.")
            response.append(gather)
            
            # Reset counter since we're now using guided approach
            context.metadata["entity_failures"] = 0
            
            # Fallback
            response.say("I didn't catch that. Thanks for calling!")
            response.hangup()
            
            return str(response)
        elif is_asking_for_dealer:
            # Increment failure counter if still asking for dealer
            context.metadata["entity_failures"] += 1
            
        # Determine the type of response and handle accordingly
        if "[final_answer]" in agent_reply:
            # This is a final answer - follow up with "anything else" prompt
            response.pause(length=1)
            
            common_phrases = "yes, no, I have another question, goodbye, thanks"
            gather = Gather(
                input="speech",
                timeout=8,
                speech_timeout="auto",
                action="/voice",
                method="POST",
                hints=common_phrases,
                speech_model="phone_call",
                language="en-US en-IN"  # Support both US and Indian English
            )
            
            gather.say("Is there anything else I can help you with today?")
            response.append(gather)
            
            # Fallback
            response.say("Thank you for calling. Goodbye!")
            response.hangup()
            
        elif "[user_input_needed]" in agent_reply:
            # Agent is asking a question - don't add an additional prompt
            # Choose hints based on the question context
            
            if "rates" in bot_reply.lower() or "APR" in bot_reply or "rate" in bot_reply.lower():
                hints = "contract rate is 7%, buy rate is 5%, apr is 6.5%, seven percent, five percent"
            elif "dealer" in bot_reply.lower() or "dealership" in bot_reply.lower():
                hints = "dealer name is Tesla, dealer is Ford, dealership is Toyota, Tesla Motors, Honda Dealership"
            else:
                hints = "yes, no, help, information, I need, I want, I'm looking for"
                
            gather = Gather(
                input="speech",
                timeout=8,
                speech_timeout="auto",
                action="/voice",
                method="POST",
                hints=hints,
                speech_model="phone_call",
                language="en-US en-IN"
            )
            
            # Don't add any additional text - just gather the next input
            response.append(gather)
            
            # Fallback
            response.say("I didn't catch that. Thanks for calling!")
            response.hangup()
            
        else:
            # Regular response - add standard follow-up
            common_phrases = "yes, no, help, information, schedule, appointment, cancel, confirm"
            gather = Gather(
                input="speech",
                timeout=8,
                speech_timeout="auto",
                action="/voice",
                method="POST",
                hints=common_phrases,
                speech_model="phone_call",
                language="en-US en-IN"
            )
            
            gather.say("What else would you like to know?")
            response.append(gather)
            
            # Fallback
            response.say("I didn't catch that. Thanks for calling!")
            response.hangup()

    else:
        # Initial interaction
        common_greeting_responses = "help me with, I need information, I have a question, I'd like to know"
        
        gather = Gather(
            input="speech",
            timeout=8,
            speech_timeout="auto",
            action="/voice",
            method="POST",
            hints=common_greeting_responses,
            speech_model="phone_call",
            language="en-US en-IN"
        )
        
        gather.say("Hey there, how can I assist you today?")
        response.append(gather)
        response.say("I didn't hear anything. Goodbye.")
        response.hangup()

    return str(response)


@app.get("/")
async def root():
    return {"message": "Automotive Assistant API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)