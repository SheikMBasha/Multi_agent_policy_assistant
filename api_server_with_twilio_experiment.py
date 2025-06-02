# api_server.py
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union
import time
import os
import re
import datetime
import random  # Import random at the top level
from twilio.twiml.voice_response import VoiceResponse, Gather

# Import your agent system
from config.llm_config import get_llm_config
from config.system_config import get_system_config
from context.conversation_context import ConversationContext
from agents import create_agents
from tools.calculateincentivetool import CalculateIncentiveTool

#################################################
# Configuration & Initialization
#################################################

app = FastAPI(title="Automotive Assistant API")

# Session management
phone_sessions = {}

# Define common phrases for voice recognition
confirmation_phrases = ["yes", "correct", "that's right", "right", "yeah", "yep", "sure", "true"]
rejection_phrases = ["no", "wrong", "that's wrong", "not right", "nope", "false", "incorrect"]

# Initialize agent system
context = ConversationContext()
llm_config = get_llm_config()
system_config = get_system_config()
incentive_tool = CalculateIncentiveTool(api_url="http://localhost:8000")
agents = create_agents(llm_config, context, incentive_tool)

#################################################
# Data Models
#################################################

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

#################################################
# Speech Recognition Utilities
#################################################

def preprocess_speech_input(text: str) -> str:
    """
    Normalize and clean speech recognition text with context awareness
    
    Args:
        text: The raw speech recognition text
        
    Returns:
        Processed text with corrections applied
    """
    if not text:
        return text
    
    # Basic corrections
    corrections = {
        "deal or": "dealer",
        "dealers": "dealer is",
        "dealer ship": "dealership",
        "percentage": "percent",
        "percent is": "percent",
        "percent age": "percentage",
        "prestige motor": "prestige motors",
        "groupon auto": "groupon automotive",
        "sonic auto": "sonic automotive",
        "Sony Automotive": "Sonic Automotive",
        "lithium motor": "lithium motors",
    }
    
    # Apply corrections
    processed = text
    for wrong, correct in corrections.items():
        processed = re.sub(r'\b' + wrong + r'\b', correct, processed, flags=re.IGNORECASE)

    # Context-aware "dear" correction
    automotive_contexts = [
        r'dear compensation',
        r'dear incentive',
        r'dear commission', 
        r'dear rebate',
        r'my dear \w+',
        r'from dear', 
        r'at dear'
    ]

    for context_pattern in automotive_contexts:
        processed = re.sub(context_pattern, 
                           lambda m: m.group(0).replace('dear', 'dealer'), 
                           processed, flags=re.IGNORECASE)
        
    return processed

def create_optimized_gather(prompt_text: str, 
                           context_type: Optional[str] = None, 
                           session_id: Optional[str] = None) -> Gather:
    """
    Create an optimized Gather object with context-specific configuration
    
    Args:
        prompt_text: Text to speak to the user
        context_type: Type of context (dealer, rates, greeting, etc.)
        session_id: Session ID for context retrieval
        
    Returns:
        Configured Gather object
    """
    # Get session context if provided
    context = phone_sessions.get(session_id, None) if session_id else None
    failure_count = context.metadata.get("entity_failures", 0) if context and hasattr(context, 'metadata') else 0
    
    # Base configuration
    base_config = {
        "input": "speech",
        "timeout": 10,
        "speech_timeout": "auto",
        "action": "/voice",
        "method": "POST",
        "language": "en-US",
        "profanity_filter": False
    }
    
    # Context-specific configurations - organized by type
    context_configs = {
        "dealer": {
            "hints": ("dealer name is Prestige Motors, dealer is Groupon Automotive, "
                     "Sonic Automotive, Lithium Motors, Tesla Motors, Honda Dealership, "
                     "Ford dealer, Toyota dealership, at Prestige Motors, from Sonic Automotive"),
            "speech_model": "experimental_utterances" if failure_count >= 2 else "googlev2_telephony"
        },
        "rates": {
            "hints": ("contract rate is 7%, buy rate is 5%, apr is 6.5%, "
                    "seven percent, five percent, six point five percent, "
                    "six and a half percent, seven point zero percent"),
            "speech_model": "googlev2_telephony"
        },
        "greeting": {
            "hints": ("help me with, I need information, I have a question, I'd like to know, "
                     "tell me about, what can you do, who are you, speak to agent, transfer to person"),
            "speech_model": "googlev2_telephony"
        },
        "followup": {
            "hints": ("yes, no, I have another question, thank you, goodbye, "
                    "that's all, I need more information, what about"),
            "speech_model": "googlev2_telephony"
        },
        "default": {
            "hints": ("yes, no, help, information, I need, I want, I'm looking for, "
                    "dealer, rates, policy, pricing, incentive"),
            "speech_model": "googlev2_telephony"
        }
    }
    
    # Apply context-specific configuration
    if context_type in context_configs:
        base_config.update(context_configs[context_type])
    else:
        base_config.update(context_configs["default"])
    
    # Create the gather object
    gather = Gather(**base_config)
    gather.say(prompt_text)
    
    return gather

def extract_dealer_name(text: str) -> Optional[str]:
    """
    Extract dealer name from user input using pattern matching
    
    Args:
        text: Processed user input
        
    Returns:
        Extracted dealer name or None if not found
    """
    # List of known dealer names for direct matching
    dealer_names = ["Prestige Motors", "Groupon Automotive", "Sonic Automotive", "Lithium Motors"]
    
    # Check for direct matches first
    for dealer in dealer_names:
        if dealer.lower() in text.lower():
            return dealer
    
    # Try pattern matching
    dealer_patterns = [
        r'\b(?:dealer|dealership) (?:is|name is) ([A-Za-z]+(?:\s+[A-Za-z]+){0,3})',
        r'(?:at|from|with) ([A-Za-z]+(?:\s+[A-Za-z]+){0,3}(?:\s+Motors|\s+Dealership|\s+Auto|\s+Cars))',
        r'\b([A-Za-z]+(?:\s+Motors|\s+Dealership|\s+Auto|\s+Cars))',
    ]
    
    for pattern in dealer_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

#################################################
# Core Message Processing
#################################################

def process_message(user_message: str, session_id: str = "default", user_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Process user message and generate appropriate response
    
    Args:
        user_message: Message from the user
        session_id: Session identifier 
        user_name: Optional user name
        
    Returns:
        Response dictionary with agent, response text, context, and timing info
    """
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
        
        # Check for special commands
        if "transfer" in user_message.lower() or "speak to agent" in user_message.lower():
            response = "[user_input_needed] I'll transfer you to a human agent. Please confirm by saying 'yes' or 'transfer'."
            elapsed_time_ms = (time.time() - start_time) * 1000
            return {
                "agent": "TransferAgent",
                "response": response,
                "context": {"action": "transfer", "user_name": context.user_name},
                "response_time_ms": elapsed_time_ms,
                "cache_hit": False
            }
        
        # Special handling for getting the user's name
        if not context.user_name:
            name = context.extract_name(user_message)
            if name:
                context.user_name = name
                response = f"Hello {name}! I'm here to help."
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
            elapsed_time_ms = (time.time() - start_time) * 1000
            return {
                "agent": "SmallTalkAgent", 
                "response": response, 
                "context": {"user_name": context.user_name},
                "response_time_ms": elapsed_time_ms,
                "cache_hit": False
            }
        
        # # Ask the moderator to determine which agent should handle this
        # selected_agent_name = agents["moderator"].determine_agent(user_message)
        # print(f"Selected agent is {selected_agent_name}")

        # Ask the moderator to determine which agent should handle this
        # NEW LINE: Change to unpack a tuple rather than just get a string
        selected_agent_name, inappropriate_category = agents["moderator"].determine_agent(user_message)
        print(f"Selected agent is {selected_agent_name}, inappropriate category: {inappropriate_category}")

        # NEW BLOCK: Handle inappropriate content if detected
        if inappropriate_category:
            inappropriate_response = agents["moderator"].get_inappropriate_response(user_message, inappropriate_category)
            elapsed_time_ms = (time.time() - start_time) * 1000
            return {
                "agent": "SmallTalkAgent",
                "response": inappropriate_response,
                "context": {"user_name": context.user_name if hasattr(context, 'user_name') else None},
                "response_time_ms": elapsed_time_ms,
                "cache_hit": False
            }
        
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
        print(f"Selected agent response is {response}")

        # Special handling for pricing agent errors
        if agent_key == "pricing" and "error" in response.lower():
            # Clear dealer information from context when an error occurs
            if hasattr(context, 'dealer_name'):
                delattr(context, 'dealer_name')

            response += " Please try again with a valid dealer name, for example: 'What is my incentive at Prestige Motors?'"
        
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
            "cache_hit": False
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
    

#################################################
# Helper Functions for Voice Flow
#################################################

async def handle_low_confidence_dealer(response: VoiceResponse, context: Any, session_id: str) -> str:
    """Handle low confidence dealer name recognition"""
    response.say("I'm having trouble understanding the dealer name. Could you repeat it more clearly?")
    
    gather = Gather(
        input="speech",
        timeout=12,  # Extended timeout
        speech_timeout="auto",
        action="/voice",
        method="POST",
        hints="dealer name is Prestige Motors, dealer is Groupon Automotive, Sonic Automotive, Lithium Motors",
        speech_model="experimental_utterances",  # Try experimental model for proper nouns
        language="en-US",
        profanity_filter=False
    )
    
    gather.say("For example, you can say 'dealer name is Prestige Motors' or 'I'm at Sonic Automotive'")
    response.append(gather)
    
    # Fallback
    response.say("I didn't catch that. Let's try a different approach.")
    return str(response)

async def handle_guided_dealer_selection(response: VoiceResponse, context: Any, session_id: str, call_sid: str) -> str:
    """Handle guided dealer selection after multiple recognition failures"""
    print("handle_guided_dealer_selection called")
    response.pause(length=1)
    response.say("I'm having trouble understanding the dealer name. Let me offer some options.")
    
    # Store the dealer options in the session for later verification
    dealer_options = ["Prestige Motors", "Groupon Automotive", "Sonic Automotive", "Lithium Motors"]
    context.metadata["dealer_options"] = dealer_options
    
    gather = Gather(
        input="speech",
        timeout=10,
        speech_timeout="auto",
        action="/voice",
        method="POST",
        hints=", ".join(dealer_options),  # Join all options as hints
        speech_model="experimental_utterances",  # Use experimental model for proper nouns
        language="en-US",
        profanity_filter=False
    )
    
    # Add a numbered list for clarity
    prompt_text = "Please choose from these dealers: "
    for i, dealer in enumerate(dealer_options, 1):
        prompt_text += f"Number {i}, {dealer}. "
        
    gather.say(prompt_text)
    response.append(gather)
    
    # Reset counter since we're now using guided approach
    context.metadata["entity_failures"] = 0
    
    # Fallback
    response.say("I didn't catch that. Thanks for calling!")
    response.hangup()
    
    return str(response)

async def handle_call_transfer(call_sid: str, context: Any, confirmation: str) -> str:
    """
    Handle transferring the call to a human agent
    
    Args:
        call_sid: Call identifier
        context: Session context
        confirmation: User confirmation input
        
    Returns:
        TwiML response as string
    """
    response = VoiceResponse()
    
    # Only proceed with transfer if explicitly confirmed
    if confirmation == "confirmed" or "yes" in confirmation.lower() or "transfer" in confirmation.lower():
        # Set the transfer destination
        transfer_number = "+918197885663" #"+918886793222" #"+919791125766"  # Replace with your actual support number
        
        # Personalized transfer message
        name_part = f", {context.user_name}" if hasattr(context, 'user_name') and context.user_name else ""
        response.say(f"Thank you{name_part}. I'll connect you with a customer service agent now. Please stay on the line.")
        
        # Record the call during transfer (optional)
        response.dial(
            transfer_number,
            action="/voice/post-transfer",
            timeout=30,  # Give 30 seconds for agent to answer
            record="record-from-answer",
            recordingStatusCallback="/recording-status"  # Optional webhook for recording status
        )
        
        # If transfer fails (e.g., no answer)
        response.say("I'm sorry, but I couldn't connect you to an agent at this time. Please try again later.")
        response.hangup()
    else:
        # User didn't confirm transfer
        response.say("I'll continue assisting you myself. What else would you like to know?")
        
        # Continue with normal flow
        gather = create_optimized_gather(
            "How can I help you today?", 
            context_type="greeting", 
            session_id=f"call_{call_sid}"
        )
        response.append(gather)
        
        # Fallback
        response.say("I didn't hear anything. Goodbye.")
        response.hangup()
    
    return str(response)

#################################################
# API Endpoints
#################################################

@app.get("/")
async def root():
    """Root endpoint health check"""
    return {"message": "Automotive Assistant API is running"}

@app.post("/chat", response_model=MessageResponse)
async def chat(request: MessageRequest):
    """Chat API endpoint for text-based interactions"""
    result = process_message(request.message, request.session_id, request.user_name)
    return result

@app.post("/voice", response_class=PlainTextResponse)
async def voice(request: Request):
    """
    Voice endpoint for Twilio voice interactions
    Handles speech processing, context management, and response generation
    """
    form = await request.form()
    user_input = form.get("SpeechResult")
    call_sid = form.get("CallSid", "unknown")
    confidence = float(form.get("Confidence", "0.0"))
    
    # Create a unique session ID for this call
    session_id = f"call_{call_sid}"
    
    # Create or get session context for this call
    if session_id not in phone_sessions:
        phone_sessions[session_id] = ConversationContext()
        # Initialize metadata for tracking entity recognition failures
        phone_sessions[session_id].metadata = {
            "entity_failures": 0,
            "recognition_metrics": {
                "dealer_mentions": 0,
                "low_confidence_count": 0
            }
        }
        print(f"Created new phone session: {session_id}")
    
    response = VoiceResponse()

    # If no user input, handle as initial interaction
    if not user_input:
        gather = create_optimized_gather(
            "Hey there, how can I assist you today?", 
            context_type="greeting"
        )
        response.append(gather)
        response.say("I didn't hear anything. Goodbye.")
        response.hangup()
        return str(response)
        
    print(f"User said: {user_input} (confidence: {confidence})")
    
    # Get context for this session
    context = phone_sessions[session_id]
    
    # Track low confidence responses
    if confidence < 0.6:
        context.metadata["recognition_metrics"]["low_confidence_count"] += 1
        print(f"Low confidence detection: {confidence}")
    
    # Check for transfer to agent request
    if "transfer" in user_input.lower() or "agent" in user_input.lower() or "person" in user_input.lower():
        return await handle_call_transfer(call_sid, context, user_input)
        
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
    
    # Always preprocess user input
    processed_input = preprocess_speech_input(user_input)
    
    # Check if we previously offered dealer options and the user might be selecting one
    if hasattr(context, 'metadata') and "dealer_options" in context.metadata and context.metadata["dealer_options"]:
        dealer_options = context.metadata["dealer_options"]
        # Check if any of our options appear in the user's message
        for dealer in dealer_options:
            if dealer.lower() in processed_input.lower():
                processed_input = f"dealer name is {dealer}"
                print(f"Matched dealer option: {dealer}, converted input to: {processed_input}")
                break
    
    # Enhanced dealer name detection patterns
    dealer_patterns = [
        # Match common car brands with more flexibility
        (r'\b(?:the|at|from|with|through)\s+(Prestige|Groupon|Sonic|Lithium|Chevrolet|Volkswagen|Audi|Nissan|Hyundai|Kia|Lexus|Mazda)(?:\s+\w+){0,2}\b', r'dealer is \1'),
        # Match any dealership indicator pattern
        (r'\b([A-Za-z]+(?:\s+[A-Za-z]+){0,2}(?:\s+Motors|\s+Dealership|\s+Auto|\s+Cars))\b', r'dealer is \1')
    ]
    
    # Check if this is likely an introduction/name sharing
    introduction_patterns = [
        r"(?:my|the|this) name is (\w+)",
        r"(?:i am|i'm) (\w+)",
        r"(?:this is|it's) (\w+)",
        r"(\w+) (?:here|speaking)",
        r"(?:my name|i'm|i am|it's|this is) (\w+)"
    ]
    
    is_introduction = any(re.search(pattern, processed_input, re.IGNORECASE) for pattern in introduction_patterns)
    
    # For non-goodbye, non-trivial queries, play an intermediary message
    # to keep the user engaged during processing
    if not is_goodbye and not any(thank_you in processed_input.lower() for thank_you in ["thank you", "thanks"]) and not is_introduction:
        # List of intermediate "checking" responses
        intermediate_responses = [
            "Let me check that for you.",
            "I'm looking into that now.",
            "Just a moment while I find that information.",
            "Let me get that answer for you.",
            "I'm retrieving that information.",
            "Give me a second to look that up.",
            "I'm searching for the best answer.",
            "Let me access that information for you.",
            "One moment while I check our database.",
            "I'm processing your question now."
        ]
        
        # Use the imported random module
        intermediate_message = random.choice(intermediate_responses)
        
        # Say the intermediate message while processing
        response.say(intermediate_message)
        
        # Add a slight pause to simulate processing time
        response.pause(length=1)
    
    # Get the agent's response using our central processing function
    try:
        print("Begin Process_message with processed input:", processed_input)
        result = process_message(processed_input, session_id)
        
        # Verify result is a dictionary
        if isinstance(result, str):
            print(f"WARNING: process_message returned a string instead of a dict: {result}")
            agent_reply = result
        else:
            agent_reply = result.get("response", "I'm sorry, I'm having trouble processing that request.")
            
        # Handle transfer agent request
        if result.get("agent") == "TransferAgent" and result.get("context", {}).get("action") == "transfer":
            if "yes" in user_input.lower() or "transfer" in user_input.lower():
                return await handle_call_transfer(call_sid, context, "confirmed")
        
        # UPDATED BLOCK: Check if this is an inappropriate content response
        # More robust detection for any category of inappropriate response
        is_inappropriate_response = False
        
        # Check for SmallTalkAgent with typical inappropriate response phrases
        if result.get("agent") == "SmallTalkAgent":
            inappropriate_phrases = [
                "I'm your automotive assistant",
                "I'm programmed to assist with automotive",
                "I'm designed to assist with",
                "I'm not designed to handle",
                "I can't provide information about",
                "I'd be happy to help you with those topics instead"
            ]
            
            if any(phrase in agent_reply for phrase in inappropriate_phrases):
                is_inappropriate_response = True
                print("Detected inappropriate content response")
        
        # Handle inappropriate content responses
        if is_inappropriate_response:
            # Say the response
            response.say(agent_reply)
            
            # Add a prompt to guide the user back to automotive topics
            follow_up_prompts = [
                "What automotive information can I help you with today?",
                "Do you have any questions about vehicle financing or policies?",
                "Is there any automotive information I can provide for you?",
                "How can I assist you with your automotive needs?"
            ]
            
            selected_prompt = random.choice(follow_up_prompts)
            
            # Create gather to collect next input
            gather = create_optimized_gather(
                selected_prompt,
                context_type="greeting",
                session_id=session_id
            )
            
            # Append the gather to keep the call going
            response.append(gather)
            
            # Fallback
            response.say("I didn't hear anything. Thank you for calling. Goodbye!")
            response.hangup()
            
            return str(response)
    except Exception as e:
        print(f"Error in process_message: {e}")
        agent_reply = f"I'm sorry, but I'm having trouble understanding. Can I help you with something else?"
    
    # Clean the tags for speaking
    bot_reply = agent_reply.replace("[final_answer]", "").replace("[user_input_needed]", "").strip()
    print(f"Bot says: {bot_reply}")

    transfer_phrases = ["transfer you to", "connect you with", "human executive", "human agent", "customer representative"]
    if any(phrase in bot_reply.lower() for phrase in transfer_phrases):
        return await handle_call_transfer(call_sid, context, "confirmed")
    
    # Say the bot's response, just a workaround, need to fix this flow later.
    if "[user_input_needed]" not in agent_reply:
        response.say(bot_reply)
    
    # Check for repeated entity recognition failures with dealer names
    is_asking_for_dealer = "dealer name" in bot_reply.lower() or "dealership" in bot_reply.lower()
    if is_asking_for_dealer and hasattr(context, 'metadata') and context.metadata["entity_failures"] >= 3:
        return await handle_guided_dealer_selection(response, context, session_id, call_sid)
    elif is_asking_for_dealer and hasattr(context, 'metadata'):
        # Increment failure counter if still asking for dealer
        context.metadata["entity_failures"] += 1
    
    # Determine the type of response and handle accordingly    
    # For introductions, we need to capture the next input without saying "thank you for calling"
    if is_introduction:
        # After greeting introduction, ask an open-ended question to encourage next input
        gather = create_optimized_gather(
            "How can I help you today?", 
            context_type="greeting", 
            session_id=session_id
        )
        response.append(gather)
        
        # Fallback
        response.say("I didn't hear anything. Goodbye.")
        response.hangup()
    elif "[final_answer]" in agent_reply:
        # This is a final answer - follow up with varied "anything else" prompts
        response.pause(length=1)
        
        # List of follow-up prompts to choose from randomly
        follow_up_prompts = [
            "Is there anything else I can help you with today?",
            "What other questions can I answer for you?",
            "Can I assist you with anything else?",
            "Do you have any other automotive questions I can help with?",
            "Is there something else you'd like to know about our services?",
            "Would you like information on any other topics?",
            "How else can I be of assistance today?",
            "Any other automotive questions I can answer for you?",
            "What else would you like to learn about our offerings?",
            "Is there another topic you'd like to discuss?"
        ]
        
        # Choose a random follow-up prompt
        selected_prompt = random.choice(follow_up_prompts)
        
        gather = create_optimized_gather(
            selected_prompt, 
            context_type="followup", 
            session_id=session_id
        )
        response.append(gather)
        
        # Fallback
        response.say("Thank you for calling. Goodbye!")
        response.hangup()
        
    elif "[user_input_needed]" in agent_reply:
        # Agent is asking a question - don't add an additional prompt
        # Choose context based on the question content
        context_type = None
        print("UserInputneeded block triggered.")

        print("user input needed block called")
        
        if "rates" in bot_reply.lower() or "APR" in bot_reply or "rate" in bot_reply.lower():
            context_type = "rates"
        elif "dealer" in bot_reply.lower() or "dealership" in bot_reply.lower():
            context_type = "dealer"
        else:
            context_type = "default"

        print(f"context_type chosen is {context_type}")
                
        gather = create_optimized_gather(bot_reply, context_type=context_type, session_id=session_id)
        print("Response append begin 759")
        response.append(gather)
        print("Response append end 759")
        
        # Fallback
        response.pause(length=1)
        response.say("I didn't catch that. Thanks for calling!")
        response.hangup()
        
    else:
        # Regular response - add a standard follow-up instead of hanging up
        # CHANGED: Don't hang up but ask if there's anything else
        response.pause(length=1)
        
        gather = create_optimized_gather(
            "Is there anything else I can help you with?", 
            context_type="followup", 
            session_id=session_id
        )
        response.append(gather)
        
        # Fallback
        response.say("Thank you for calling. Goodbye!")
        response.hangup()

    return str(response)

@app.post("/voice/dealer_recognition", response_class=PlainTextResponse)
async def dealer_recognition(request: Request):
    """
    Specialized endpoint for dealer name recognition
    Uses enhanced processing for better dealer name extraction
    """
    form = await request.form()
    user_input = form.get("SpeechResult")
    call_sid = form.get("CallSid", "unknown")
    confidence = float(form.get("Confidence", "0.0"))
    
    # Create a unique session ID for this call
    session_id = f"call_{call_sid}"
    
    response = VoiceResponse()
    
    if session_id not in phone_sessions:
        # Should not happen, but handle just in case
        response.say("I'm sorry, but your session has expired. Please call back.")
        response.hangup()
        return str(response)
    
    context = phone_sessions[session_id]
    
    if not user_input:
        response.say("I didn't hear anything. Let's try again.")
        gather = create_optimized_gather(
            "Please tell me the dealer name clearly.", 
            context_type="dealer", 
            session_id=session_id
        )
        response.append(gather)
        return str(response)
    
    # Enhanced processing for dealer names
    processed_input = preprocess_speech_input(user_input)
    
    # Direct pattern matching for dealer names
    dealer_names = ["Prestige Motors", "Groupon Automotive", "Sonic Automotive", "Lithium Motors"]
    
    found_dealer = None
    for dealer in dealer_names:
        if dealer.lower() in processed_input.lower():
            found_dealer = dealer
            break
    
    if found_dealer:
        # Successfully identified dealer
        response.say(f"Great! I've got {found_dealer}. Let me check that information.")
        
        # Construct a clean dealer mention and process it
        clean_input = f"dealer name is {found_dealer}"
        
        # Redirect to main voice handler with the confirmed dealer
        response.redirect(f"/voice?SpeechResult={clean_input}&CallSid={call_sid}&Confidence=0.95")
    else:
        # Try to extract any dealer-like patterns
        extracted_dealer = extract_dealer_name(processed_input)
        
        if extracted_dealer:
            # Found something that looks like a dealer
            response.say(f"I heard {extracted_dealer}. Is that correct?")
            
            # Create confirmation gather
            gather = Gather(
                input="speech",
                timeout=8,
                speech_timeout="auto",
                action="/voice/confirm_dealer",
                method="POST",
                hints="yes, correct, that's right, no, wrong, that's wrong",
                speech_model="googlev2_telephony",
                language="en-US",
                profanity_filter=False
            )
            
            # Store the candidate dealer for confirmation
            context.metadata["candidate_dealer"] = extracted_dealer
            
            gather.say("Please say yes or no.")
            response.append(gather)
        else:
            # Still couldn't understand
            response.say("I'm still having trouble understanding the dealer name.")
            
            # Increment failure counter
            context.metadata["entity_failures"] = context.metadata.get("entity_failures", 0) + 1
            
            # Check if we should switch to guided selection
            if context.metadata["entity_failures"] >= 3:
                response.redirect("/voice?SpeechResult=show%20dealer%20options&CallSid=" + call_sid)
            else:
                # Try again with more guidance
                gather = create_optimized_gather(
                    "Please say the dealer name clearly, like 'Prestige Motors' or 'Sonic Automotive'.", 
                    context_type="dealer", 
                    session_id=session_id
                )
                response.append(gather)
    
    return str(response)

@app.post("/voice/confirm_dealer", response_class=PlainTextResponse)
async def confirm_dealer(request: Request):
    """Endpoint to confirm dealer name extraction"""
    form = await request.form()
    user_input = form.get("SpeechResult", "").lower()
    call_sid = form.get("CallSid", "unknown")
    
    # Create a unique session ID for this call
    session_id = f"call_{call_sid}"
    
    response = VoiceResponse()
    
    if session_id not in phone_sessions:
        # Should not happen, but handle just in case
        response.say("I'm sorry, but your session has expired. Please call back.")
        response.hangup()
        return str(response)
    
    context = phone_sessions[session_id]
    candidate_dealer = context.metadata.get("candidate_dealer")
    
    if not candidate_dealer:
        # No candidate dealer stored
        response.say("I'm sorry, there was an error processing your dealer information.")
        response.redirect("/voice?SpeechResult=dealer%20error&CallSid=" + call_sid)
        return str(response)
    
    # Check if the user confirmed
    if any(phrase in user_input for phrase in confirmation_phrases):
        # User confirmed
        response.say(f"Great! I've registered {candidate_dealer} as your dealer.")
        
        # Clean up metadata
        clean_input = f"dealer name is {candidate_dealer}"
        
        # Redirect to main voice handler with the confirmed dealer
        response.redirect(f"/voice?SpeechResult={clean_input}&CallSid={call_sid}&Confidence=0.95")
    elif any(phrase in user_input for phrase in rejection_phrases):
        # User rejected
        response.say("I apologize for the confusion. Let me offer you some options.")
        
        # Increment failure counter
        context.metadata["entity_failures"] = context.metadata.get("entity_failures", 0) + 1
        
        # Switch to guided selection
        response.redirect("/voice?SpeechResult=show%20dealer%20options&CallSid=" + call_sid)
    else:
        # Unclear response
        response.say("I didn't understand your response.")
        
        gather = Gather(
            input="speech",
            timeout=8,
            speech_timeout="auto",
            action="/voice/confirm_dealer",
            method="POST",
            hints="yes, correct, that's right, no, wrong, that's wrong",
            speech_model="googlev2_telephony",
            language="en-US",
            profanity_filter=False
        )
        
        gather.say(f"Was {candidate_dealer} correct? Please say yes or no.")
        response.append(gather)
    
    return str(response)

@app.post("/voice/transfer", response_class=PlainTextResponse)
async def voice_transfer(request: Request):
    """
    Endpoint for transferring calls to a human agent
    Forwards the call to the specified phone number
    """
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    
    # Create a unique session ID for this call
    session_id = f"call_{call_sid}"
    
    response = VoiceResponse()
    
    # Forward to customer service number
    agent_number = "+18005551234"  # Replace with your agent's number
    
    response.say("Transferring you to a customer service agent. Please hold.")
    response.dial(agent_number, timeout=30, record="record-from-ringing")
    
    # Clean up the session
    if session_id in phone_sessions:
        del phone_sessions[session_id]
    
    return str(response)

@app.post("/voice/post-transfer", response_class=PlainTextResponse)
async def post_transfer(request: Request):
    """Handle post-transfer actions"""
    form = await request.form()
    call_sid = form.get("CallSid", "unknown")
    dial_status = form.get("DialCallStatus", "completed")
    
    response = VoiceResponse()
    
    # Check if the transfer was successful
    if dial_status == "completed" or dial_status == "answered":
        # Call was successful, just hang up
        response.hangup()
    else:
        # Transfer failed
        response.say("I couldn't connect you to an agent. Would you like to leave a voicemail?")
        
        gather = Gather(
            input="speech",
            timeout=5,
            speech_timeout="auto",
            action="/voice/handle-voicemail",
            method="POST",
            hints="yes, no",
            speech_model="googlev2_telephony",
            language="en-US"
        )
        
        gather.say("Please say yes or no.")
        response.append(gather)
        
        # Fallback
        response.say("I didn't hear anything. Goodbye.")
        response.hangup()
    
    return str(response)

@app.post("/voice/handle-voicemail", response_class=PlainTextResponse)
async def handle_voicemail(request: Request):
    """Handle voicemail recording after failed transfer"""
    form = await request.form()
    speech_result = form.get("SpeechResult", "").lower()
    
    response = VoiceResponse()
    
    if "yes" in speech_result:
        response.say("Please leave your message after the beep. Press any key when you're finished.")
        
        # Record the voicemail
        response.record(
            timeout=30,
            transcribe=True,
            transcribeCallback="/transcription-callback",
            maxLength=120,
            action="/voice/voicemail-complete",
            finishOnKey="123456789*0#"
        )
        
        # Fallback
        response.say("I didn't receive a recording. Goodbye.")
        response.hangup()
    else:
        response.say("Thank you for calling. A customer service representative will follow up with you soon. Goodbye.")
        response.hangup()
    
    return str(response)

@app.post("/voice/voicemail-complete", response_class=PlainTextResponse)
async def voicemail_complete(request: Request):
    """Handle completion of voicemail recording"""
    form = await request.form()
    recording_url = form.get("RecordingUrl")
    
    response = VoiceResponse()
    
    if recording_url:
        response.say("Thank you for your message. A customer service representative will get back to you soon.")
    else:
        response.say("I didn't receive your message. Please try calling back later.")
    
    response.hangup()
    return str(response)

#################################################
# Main Application Entry Point
#################################################

if __name__ == "__main__":
    print("Starting Automotive Assistant API server on port 5001...")
    uvicorn.run(app, host="0.0.0.0", port=5001)