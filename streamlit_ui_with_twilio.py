# streamlit_ui.py
import streamlit as st
import requests
import speech_recognition as sr
import pyttsx3
import threading
import uuid
import time
import os
from dotenv import load_dotenv
from twilio.rest import Client

# Load environment variables
load_dotenv()

# API configuration
API_URL = "http://localhost:5001"

# Twilio configuration
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")  # Twilio number
to_number = os.getenv("TWILIO_TO_PHONE_NUMBER")  # Default recipient number

# Initialize Twilio client if credentials are available
twilio_enabled = all([account_sid, auth_token, twilio_number])
if twilio_enabled:
    try:
        client = Client(account_sid, auth_token)
    except Exception as e:
        print(f"Error initializing Twilio client: {e}")
        twilio_enabled = False
else:
    print("Twilio not configured - call button will be disabled")

# Create a unique engine for each session
def get_engine():
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 0.9)
    return engine

def speak(text):
    """Text-to-speech function that creates a new engine instance each time"""
    # Clean the text by removing any markdown or special tags
    cleaned_text = text.replace("[final_answer]", "").strip()

    def speak_thread():
        try:
            # Always create a fresh engine instance
            engine = get_engine()
            engine.say(cleaned_text)
            engine.runAndWait()
            # Important: explicitly delete the engine after use
            del engine
        except Exception as e:
            print(f"Speech error: {e}")

    # Run in a separate thread
    thread = threading.Thread(target=speak_thread)
    thread.daemon = True
    thread.start()
    # Give it a moment to start speaking
    time.sleep(0.1)

# Function to make a call using Twilio
def make_twilio_call():
    if not twilio_enabled:
        return False, "Twilio is not configured"
    
    try:
        call = client.calls.create(
            to=to_number,
            from_=twilio_number,
            url="https://9f9b-2401-4900-8fce-4980-3c47-2962-6948-f4d5.ngrok-free.app/voice"
        )
        return True, call.sid
    except Exception as e:
        return False, str(e)

# Record with speech_recognition
def record_audio_sr():
    r = sr.Recognizer()
    r.pause_threshold = 2.5  # Waits for this much silence before ending

    with sr.Microphone(sample_rate=16000) as source:
        st.info("🎤 Listening... Speak now. Stay silent to finish.")
        audio = r.listen(source)  # Ends when silence reaches pause_threshold

    try:
        text = r.recognize_google(audio)
    except sr.UnknownValueError:
        text = "(Could not understand audio)"
    return text

# Send message to API and get response
def send_message(message, session_id="default"):
    try:
        # Include the user's name in the request if available
        payload = {
            "message": message, 
            "session_id": session_id,
            "debug_cache": True  # Request cache debugging info
        }
        
        # Add user name to the payload if available
        if st.session_state.get("user_name"):
            payload["user_name"] = st.session_state.user_name
        
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/chat", 
            json=payload
        )
        response_time = time.time() - start_time
        response.raise_for_status()
        
        response_data = response.json()
        
        # Add debug info about potential caching
        if response_time < 0.1:  # Less than 100ms usually indicates caching
            response_data["_debug_info"] = f"Response time: {response_time:.3f}s (likely cached)"
        else:
            response_data["_debug_info"] = f"Response time: {response_time:.3f}s"
            
        # Check if there's explicit cache info from the backend
        if "cache_hit" in response_data:
            response_data["_debug_info"] += f" | Cache: {'Hit' if response_data['cache_hit'] else 'Miss'}"
        
        # If the response contains user_name in context, update our state
        if response_data.get("context", {}).get("user_name"):
            if not st.session_state.get("user_name"):
                st.session_state.user_name = response_data["context"]["user_name"]
                print(f"Updated user name from API: {st.session_state.user_name}")
        
        return response_data
    except Exception as e:
        st.error(f"Error communicating with backend: {e}")
        return {"agent": "System", "response": "Sorry, I'm having trouble connecting to the backend system."}

# Check if a message indicates the user is done with the conversation
def is_conversation_ending_indication(message):
    message = message.lower()
    ending_phrases = [
        "i am good", "i'm good", "that's all", "that is all", "no thanks", 
        "i'm done", "i am done", "goodbye", "bye", "we're done", "we are done",
        "that'll be all", "that will be all", "no, i am good", "no i'm good"
    ]
    
    for phrase in ending_phrases:
        if phrase in message:
            return True
    
    return False

# Streamlit UI
st.set_page_config(page_title="WAVE", layout="centered")

st.markdown("<h1 style='text-align: center;'>🚗 AutoFinance Virtual Engagement</h1>", unsafe_allow_html=True)
st.markdown("---")

# Check if API is reachable
try:
    health_check = requests.get(f"{API_URL}/")
    if health_check.status_code != 200:
        st.error(f"Backend API is not responding correctly. Status code: {health_check.status_code}")
        st.stop()
except Exception as e:
    st.error(f"Cannot connect to backend API at {API_URL}. Please make sure the server is running.")
    st.error(f"Error: {e}")
    st.stop()

# Session state initialization
if "chat" not in st.session_state:
    st.session_state.chat = []
    # Add the initial greeting
    st.session_state.chat.append(("Agent", "Hello! Welcome to our automotive assistant. May I know your name, please?"))
    
if "thinking" not in st.session_state:
    st.session_state.thinking = False
if "speak_text" not in st.session_state:
    st.session_state.speak_text = None
if "speech_id" not in st.session_state:
    st.session_state.speech_id = None
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "closing_confirmation" not in st.session_state:
    st.session_state.closing_confirmation = False
if "conversation_ended" not in st.session_state:
    st.session_state.conversation_ended = False
if "waiting_for_closing_response" not in st.session_state:
    st.session_state.waiting_for_closing_response = False
if "mic_clicked" not in st.session_state:
    st.session_state.mic_clicked = False
if "call_status" not in st.session_state:
    st.session_state.call_status = None
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "show_debug_info" not in st.session_state:
    st.session_state.show_debug_info = False

# Check if we need to speak something (with ID to prevent repetition)
current_speech_id = st.session_state.speech_id
if st.session_state.speak_text:
    speak(st.session_state.speak_text)
    # Clear after speaking to prevent repetition
    st.session_state.speak_text = None
    # Update speech ID to prevent repeats
    st.session_state.speech_id = str(uuid.uuid4())

# Display chat history
st.subheader("🗨️ Conversation")
for sender, message in st.session_state.chat:
    if sender == "You":
        st.markdown(f"**{sender}**: {message}")
    elif sender == "_debug_info" and st.session_state.show_debug_info:
        # Display debug info in smaller, gray text
        st.markdown(f"<span style='color:gray; font-size:0.8em;'>{message}</span>", unsafe_allow_html=True)
    else:
        # Format agent messages
        cleaned_message = message.replace("[final_answer]", "")
        st.markdown(f"**{sender}**: {cleaned_message}")

# Display call status if available
if st.session_state.call_status:
    success, details = st.session_state.call_status
    if success:
        st.success(f"📞📲 Call initiated successfully! Call ID: {details}")
    else:
        st.error(f"❌ Call failed: {details}")

if st.session_state.thinking:
    st.markdown("**Assistant**: 🤔 ...thinking")

st.markdown("---")

# Don't show input if conversation has ended
if not st.session_state.get("conversation_ended", False):
    # --- Form: Text Input and Buttons ---
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("Type your message", key="input_box", label_visibility="collapsed")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            send_clicked = st.form_submit_button("Send")
        with col2:
            mic_clicked = st.form_submit_button("🎤")
        with col3:
            call_clicked = st.form_submit_button("📞 Call", disabled=not twilio_enabled)
    
    # --- Call Button Handling ---
    if 'call_clicked' in locals() and call_clicked:
        success, details = make_twilio_call()
        st.session_state.call_status = (success, details)
        st.rerun()
    
    # --- Mic Click Handling ---
    if st.session_state.get("mic_clicked", False) or ('mic_clicked' in locals() and mic_clicked):
        transcribed_text = record_audio_sr()
        st.session_state.chat.append(("You", transcribed_text))
        st.session_state.thinking = True
        st.session_state.mic_clicked = False
        st.rerun()

    # --- Text Input Handling ---
    if 'send_clicked' in locals() and send_clicked and user_input.strip():
        st.session_state.chat.append(("You", user_input.strip()))
        st.session_state.thinking = True
        st.rerun()
else:
    st.info("This conversation has ended. Refresh the page or click 'Reset Conversation' in the sidebar to start a new one.")

# --- Bot Response Handler ---
if st.session_state.thinking:
    user_message = st.session_state.chat[-1][1]
    
    # Check if we're in closing confirmation mode
    if st.session_state.waiting_for_closing_response:
        user_response = user_message.lower()
        
        if any(word in user_response for word in ["yes", "yeah", "yep", "sure", "ok", "okay", "y"]):
            # User confirmed they want to end the conversation
            farewell = "Thank you for using our Automotive Assistant. Have a great day!"
            st.session_state.chat.append(("Assistant", farewell))
            st.session_state.speak_text = farewell
            st.session_state.conversation_ended = True
            st.session_state.waiting_for_closing_response = False
        elif any(word in user_response for word in ["no", "nope", "n", "continue"]):
            # User wants to continue the conversation
            continue_msg = "Great! How else can I assist you today?"
            st.session_state.chat.append(("Assistant", continue_msg))
            st.session_state.speak_text = continue_msg
            st.session_state.waiting_for_closing_response = False
        else:
            # If we couldn't determine yes/no, just process as a normal query
            st.session_state.waiting_for_closing_response = False
            # Continue with normal processing (don't return)
        
        if st.session_state.waiting_for_closing_response == False:
            st.session_state.thinking = False
            st.rerun()
    
    # Check if this is a closing indication from user
    elif is_conversation_ending_indication(user_message):
        # Add confirmation message
        confirmation_message = "Would you like to end this conversation? (Yes/No)"
        st.session_state.chat.append(("Assistant", confirmation_message))
        st.session_state.speak_text = confirmation_message
        st.session_state.thinking = False
        st.session_state.waiting_for_closing_response = True
        st.rerun()
    
    # Regular message processing
    else:
        try:
            # Get response from backend API
            response_data = send_message(user_message, st.session_state.session_id)
            
            agent_name = response_data.get("agent", "Assistant")
            message = response_data.get("response", "Sorry, something went wrong.")
            
            # Add to chat history
            st.session_state.chat.append((agent_name, message))
            
            # Add debug info to the chat if it exists
            if "_debug_info" in response_data and st.session_state.show_debug_info:
                st.session_state.chat.append(("_debug_info", response_data["_debug_info"]))
            
            # Check if this is a final answer (but not a question)
            if "[final_answer]" in message and "?" not in message:
                # Automatically ask if there's anything else to help with
                follow_up = "Is there anything else I can help you with today?"
                st.session_state.chat.append(("Assistant", follow_up))
                st.session_state.speak_text = message + " " + follow_up
            else:
                # Regular response - just speak the message
                st.session_state.speak_text = message
        except Exception as e:
            st.session_state.chat.append(("System", f"Error: {str(e)}"))
            st.session_state.speak_text = "I'm having trouble processing your request."
        
        st.session_state.thinking = False
        st.rerun()

# Add debugging options in the sidebar
with st.sidebar:
    st.title("Assistant Settings")
    
    st.subheader("Voice Options")
    voice_enabled = st.checkbox("Enable Voice Output", value=True)
    if not voice_enabled:
        st.session_state.speak_text = None
    
    # Test button with unique ID to ensure it always works
    if st.button(f"Test Speech"):
        st.session_state.speak_text = "This is a test of the speech system."
        st.session_state.speech_id = str(uuid.uuid4())
        st.rerun()

    # Force new engine creation
    if st.button("Reset Speech Engine"):
        st.session_state.speech_id = str(uuid.uuid4())
        st.success("Speech engine reset.")
        st.rerun()
    
    if twilio_enabled:
        st.subheader("Call Settings")
        recipient_number = st.text_input("Recipient Phone Number", value=to_number if to_number else "+1234567890", 
                                       help="Enter the phone number to call (with country code)")
        
        if st.button("Update Call Number"):
            to_number = recipient_number
            st.success(f"Call number updated to {to_number}")
    else:
        st.subheader("Call Settings")
        st.warning("Twilio is not configured. Set environment variables to enable calling.")
    
    st.subheader("Debug Settings")
    st.session_state.show_debug_info = st.checkbox("Show Response Debug Info", value=st.session_state.show_debug_info)
    
    st.subheader("Connection Info")
    st.write(f"API URL: {API_URL}")
    st.write(f"Session ID: {st.session_state.session_id}")
    if st.session_state.user_name:
        st.write(f"User Name: {st.session_state.user_name}")
    
    if st.button("Reset Conversation"):
        st.session_state.chat = []
        st.session_state.chat.append(("SmallTalkAgent", "Hello! Welcome to our automotive assistant. May I know your name, please?"))
        # Generate a new session ID
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.conversation_ended = False
        st.session_state.waiting_for_closing_response = False
        st.session_state.call_status = None
        st.session_state.user_name = None
        st.success("Conversation reset!")
        st.rerun()