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

# Helper function to create optimized speech recognition gatherers
def create_optimized_gather(prompt_text, context_type=None, session_id=None):
    """Create an optimized Gather object with context-specific configuration"""
    
    # Get session context if provided
    context = phone_sessions.get(session_id, None) if session_id else None
    failure_count = context.metadata.get("entity_failures", 0) if context and hasattr(context, 'metadata') else 0
    
    # Base configuration
    base_config = {
        "input": "speech",
        "timeout": 10,  # Longer timeout for better recognition
        "speech_timeout": "auto",
        "action": "/voice",
        "method": "POST",
        "language": "en-US",  # Single language code for better recognition
        "profanity_filter": False  # Disable for better accuracy
    }
    
    # Context-specific configuration
    if context_type == "dealer":
        # Dealer name specific configuration
        base_config.update({
            "hints": ("dealer name is Prestige Motors, dealer is Groupon Automotive, "
                      "Sonic Automotive, Lithium Motors, Tesla Motors, Honda Dealership, "
                      "Ford dealer, Toyota dealership, at Prestige Motors, from Sonic Automotive"),
            "speech_model": "experimental_utterances" if failure_count >= 2 else "googlev2_telephony"
        })
    elif context_type == "rates":
        # Rates/numbers specific configuration
        base_config.update({
            "hints": ("contract rate is 7%, buy rate is 5%, apr is 6.5%, "
                     "seven percent, five percent, six point five percent, "
                     "six and a half percent, seven point zero percent"),
            "speech_model": "googlev2_telephony"  # Good for numbers
        })
    elif context_type == "greeting":
        # Initial greeting configuration
        base_config.update({
            "hints": ("help me with, I need information, I have a question, I'd like to know, "
                      "tell me about, what can you do, who are you"),
            "speech_model": "googlev2_telephony"
        })
    elif context_type == "followup":
        # Follow-up question configuration
        base_config.update({
            "hints": ("yes, no, I have another question, thank you, goodbye, "
                     "that's all, I need more information, what about"),
            "speech_model": "googlev2_telephony"
        })
    else:
        # Default configuration
        base_config.update({
            "hints": ("yes, no, help, information, I need, I want, I'm looking for, "
                     "dealer, rates, policy, pricing, incentive"),
            "speech_model": "googlev2_telephony"
        })
    
    # Create the gather object
    gather = Gather(**base_config)
    gather.say(prompt_text)
    
    return gather

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

        if agent_key == "pricing" and "error" in response.lower():
            #Clear dealer information from context when an error occurs.
            if hasattr(context, 'dealer_name'):
                delattr(context,'dealer_name')

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

# Function to preprocess speech recognition input
def preprocess_speech_input(text):
    """Normalize and clean speech recognition text"""
    if not text:
        return text
    
    # Standardize common misrecognitions
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
        "Sony Automotive": "Sonic Automotive",  # Specifically fix Sony vs Sonic confusion
        "lithium motor": "lithium motors",
    }
    
    # Apply corrections
    processed = text
    for wrong, correct in corrections.items():
        processed = re.sub(r'\b' + wrong + r'\b', correct, processed, flags=re.IGNORECASE)

    # Context-aware "dear" correction
    # Only replace "dear" with "dealer" in specific automotive contexts
    automotive_contexts = [
        r'dear compensation',
        r'dear incentive',
        r'dear commission',
        r'dear rebate',
        r'my dear \w+',  # "my dear [something]" in automotive context likely means "my dealer [something]" 
        r'from dear', 
        r'at dear'
    ]

    for context_pattern in automotive_contexts:
        # Replace "dear" with "dealer" only in these specific contexts
        processed = re.sub(context_pattern, lambda m: m.group(0).replace('dear', 'dealer'), 
                          processed, flags=re.IGNORECASE)
        
    return processed

@app.post("/voice", response_class=PlainTextResponse)
async def voice(request: Request):
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

    if user_input:
        print(f"User said: {user_input} (confidence: {confidence})")
        
        # Get context for this session
        context = phone_sessions[session_id]
        
        # Track low confidence responses
        if confidence < 0.6:
            context.metadata["recognition_metrics"]["low_confidence_count"] += 1
            print(f"Low confidence detection: {confidence}")
        
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
        
        for pattern, replacement in dealer_patterns:
            if re.search(pattern, processed_input, re.IGNORECASE):
                processed_input = re.sub(pattern, replacement, processed_input, flags=re.IGNORECASE)
                context.metadata["recognition_metrics"]["dealer_mentions"] += 1
                print(f"Normalized dealer input: {processed_input}")
        
        # Low confidence handling for dealer mentions
        dealer_words = ["dealer", "dealership", "motors", "automotive", "cars", "auto"]
        has_dealer_word = any(word in processed_input.lower() for word in dealer_words)
        
        if has_dealer_word and confidence < 0.6:
            # Low confidence for dealer-related input
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
        except Exception as e:
            print(f"Error in process_message: {e}")
            agent_reply = f"I'm sorry, but I'm having trouble understanding. Can I help you with something else?"
        
        # Clean the tags for speaking
        bot_reply = agent_reply.replace("[final_answer]", "").replace("[user_input_needed]", "").strip()
        print(f"Bot says: {bot_reply}")
        
        # Say the bot's response
        response.say(bot_reply)
        
        # Check for repeated entity recognition failures with dealer names
        is_asking_for_dealer = "dealer name" in bot_reply.lower() or "dealership" in bot_reply.lower()
        if is_asking_for_dealer and hasattr(context, 'metadata') and context.metadata["entity_failures"] >= 3:
            # Switch to guided approach after multiple failures
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
        elif is_asking_for_dealer and hasattr(context, 'metadata'):
            # Increment failure counter if still asking for dealer
            context.metadata["entity_failures"] += 1
            
        # Determine the type of response and handle accordingly
        if "[final_answer]" in agent_reply:
            # This is a final answer - follow up with "anything else" prompt
            response.pause(length=1)
            
            common_phrases = "yes, no, I have another question, goodbye, thanks"
            gather = create_optimized_gather(
                "Is there anything else I can help you with today?", 
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
            
            if "rates" in bot_reply.lower() or "APR" in bot_reply or "rate" in bot_reply.lower():
                context_type = "rates"
            elif "dealer" in bot_reply.lower() or "dealership" in bot_reply.lower():
                context_type = "dealer"
            else:
                context_type = None
                
            gather = create_optimized_gather("", context_type=context_type, session_id=session_id)
            response.append(gather)
            
            # Fallback
            response.say("I didn't catch that. Thanks for calling!")
            response.hangup()
            
        else:
            # Regular response - add standard follow-up
            gather = create_optimized_gather("What else would you like to know?", session_id=session_id)
            response.append(gather)
            
            # Fallback
            response.say("I didn't catch that. Thanks for calling!")
            response.hangup()

    else:
        # Initial interaction
        gather = create_optimized_gather(
            "Hey there, how can I assist you today?", 
            context_type="greeting"
        )
        response.append(gather)
        response.say("I didn't hear anything. Goodbye.")
        response.hangup()

    return str(response)

# Specialty endpoint for dealer name recognition
@app.post("/voice/dealer_recognition", response_class=PlainTextResponse)
async def dealer_recognition(request: Request):
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
        
        # Redirect to main voice handler with the clean input
        response.redirect(f"/voice?SpeechResult={clean_input}&CallSid={call_sid}&Confidence=0.95")
    else:
        # Try to extract any dealer-like patterns
        dealer_patterns = [
            r'\b(?:dealer|dealership) (?:is|name is) ([A-Za-z]+(?:\s+[A-Za-z]+){0,3})',
            r'(?:at|from|with) ([A-Za-z]+(?:\s+[A-Za-z]+){0,3}(?:\s+Motors|\s+Dealership|\s+Auto|\s+Cars))',
            r'\b([A-Za-z]+(?:\s+Motors|\s+Dealership|\s+Auto|\s+Cars))',
        ]
        
        extracted_dealer = None
        for pattern in dealer_patterns:
            match = re.search(pattern, processed_input, re.IGNORECASE)
            if match:
                extracted_dealer = match.group(1)
                break
        
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

# Endpoint to confirm dealer name
@app.post("/voice/confirm_dealer", response_class=PlainTextResponse)
async def confirm_dealer(request: Request):
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
    confirmation_phrases = ["yes", "correct", "that's right", "right", "yeah", "yep", "sure", "true"]
    rejection_phrases = ["no", "wrong", "that's wrong", "not right", "nope", "false", "incorrect"]
    
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

@app.get("/")
async def root():
    return {"message": "Automotive Assistant API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)