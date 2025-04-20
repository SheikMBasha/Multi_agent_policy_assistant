import os
import streamlit as st
import speech_recognition as sr
from google.cloud import dialogflow_v2 as dialogflow
from google.cloud.dialogflow_v2.types import InputAudioConfig, QueryInput, AudioEncoding, TextInput
import pyttsx3
import threading
import uuid
import time

# Google Cloud credentials
os.environ[
    "GOOGLE_APPLICATION_CREDENTIALS"] = r"D:\LearningWorkSpace\AIVoiceAssistant\intelligent-ivr-jiud-fdd92f56d16f.json"

project_id = "intelligent-ivr-jiud"
session_id = "user-session-1"
language_code = "en-in"


# Create a unique engine for each session
def get_engine():
    # Create a new engine each time
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 0.9)
    return engine


def speak(text):
    """Text-to-speech function that creates a new engine instance each time"""

    def speak_thread():
        try:
            # Always create a fresh engine instance
            engine = get_engine()
            engine.say(text)
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


# Dialogflow audio handler
def detect_intent_audio(audio_bytes):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    audio_config = InputAudioConfig(
        audio_encoding=AudioEncoding.AUDIO_ENCODING_LINEAR_16,
        language_code=language_code,
        sample_rate_hertz=16000
    )

    query_input = QueryInput(audio_config=audio_config)

    response = session_client.detect_intent(
        request={
            "session": session,
            "query_input": query_input,
            "input_audio": audio_bytes
        }
    )

    return response.query_result


# Record with speech_recognition (long as you speak)
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
    return audio.get_wav_data(), text


# Detect intent from typed text
def detect_intent_text(user_text):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    text_input = TextInput(text=user_text, language_code=language_code)
    query_input = QueryInput(text=text_input)

    response = session_client.detect_intent(
        request={"session": session, "query_input": query_input}
    )
    return response.query_result


# Streamlit UI
st.set_page_config(page_title="Smart Bank of India", layout="centered")

st.markdown("<h1 style='text-align: center;'>🏦 Smart Bank of India</h1>", unsafe_allow_html=True)
st.markdown("---")

# Session state initialization
if "chat" not in st.session_state:
    st.session_state.chat = []
if "thinking" not in st.session_state:
    st.session_state.thinking = False
if "speak_text" not in st.session_state:
    st.session_state.speak_text = None
if "speech_id" not in st.session_state:
    st.session_state.speech_id = None

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
    st.markdown(f"**{sender}**: {message}")

if st.session_state.thinking:
    st.markdown("**Bot**: 🤔 ...thinking")

st.markdown("---")

# --- Form: Text Input and Buttons ---
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your message", key="input_box", label_visibility="collapsed")
    col1, col2 = st.columns([1, 1])
    with col1:
        send_clicked = st.form_submit_button("Send")
    with col2:
        st.session_state.mic_clicked = st.form_submit_button("🎤")

# --- Mic Click Handling ---
if st.session_state.get("mic_clicked", False):
    audio_bytes, transcribed_text = record_audio_sr()
    st.session_state.chat.append(("You (voice)", transcribed_text))
    st.session_state.audio_bytes = audio_bytes
    st.session_state.from_voice = True
    st.session_state.thinking = True
    st.session_state.mic_clicked = False
    st.rerun()

# --- Text Input Handling ---
if send_clicked and user_input.strip():
    st.session_state.chat.append(("You (text)", user_input.strip()))
    st.session_state.thinking = True
    st.rerun()

# --- Bot Response Handler ---
if st.session_state.thinking:
    if st.session_state.get("from_voice", False):
        result = detect_intent_audio(st.session_state.audio_bytes)
        st.session_state.from_voice = False
    else:
        result = detect_intent_text(st.session_state.chat[-1][1])

    bot_reply = result.fulfillment_text
    st.session_state.chat.append(("Bot", bot_reply))
    st.session_state.thinking = False

    # Uncomment below for audio output.
    # Queue the text to be spoken with a unique ID
    st.session_state.speak_text = bot_reply

    # Update the UI
    st.rerun()

# Add debugging options in the sidebar
with st.sidebar:
    st.title("Testing & Debug")

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


# import os
# import streamlit as st
# import speech_recognition as sr
# from google.cloud import dialogflow_v2 as dialogflow
# from google.cloud.dialogflow_v2.types import InputAudioConfig, QueryInput, AudioEncoding, TextInput
# import pyttsx3
#
# # Google Cloud credentials
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"D:\LearningWorkSpace\AIVoiceAssistant\intelligent-ivr-jiud-fdd92f56d16f.json"
#
# project_id = "intelligent-ivr-jiud"
# session_id = "user-session-1"
# language_code = "en-in"
#
# engine = pyttsx3.init()
# def speak(text):
#     engine.say(text)
#     engine.runAndWait()
#
# # Dialogflow audio handler
# def detect_intent_audio(audio_bytes):
#     session_client = dialogflow.SessionsClient()
#     session = session_client.session_path(project_id, session_id)
#
#     audio_config = InputAudioConfig(
#         audio_encoding=AudioEncoding.AUDIO_ENCODING_LINEAR_16,
#         language_code=language_code,
#         sample_rate_hertz=16000
#     )
#
#     query_input = QueryInput(audio_config=audio_config)
#
#     response = session_client.detect_intent(
#         request={
#             "session": session,
#             "query_input": query_input,
#             "input_audio": audio_bytes
#         }
#     )
#
#     return response.query_result
#
# # Record with speech_recognition (long as you speak)
# def record_audio_sr():
#     r = sr.Recognizer()
#     r.pause_threshold = 2.5  # Waits for this much silence before ending
#
#     with sr.Microphone(sample_rate=16000) as source:
#         st.info("🎤 Listening... Speak now. Stay silent to finish.")
#         audio = r.listen(source)  # Ends when silence reaches pause_threshold
#
#     try:
#         text = r.recognize_google(audio)
#     except sr.UnknownValueError:
#         text = "(Could not understand audio)"
#     return audio.get_wav_data(), text
#
# # Detect intent from typed text
# def detect_intent_text(user_text):
#     session_client = dialogflow.SessionsClient()
#     session = session_client.session_path(project_id, session_id)
#
#     text_input = TextInput(text=user_text, language_code=language_code)
#     query_input = QueryInput(text=text_input)
#
#     response = session_client.detect_intent(
#         request={"session": session, "query_input": query_input}
#     )
#     return response.query_result
#
# # Streamlit UI
# st.set_page_config(page_title="Smart Bank of India", layout="centered")
#
# st.markdown("<h1 style='text-align: center;'>🏦 Smart Bank of India</h1>", unsafe_allow_html=True)
# st.markdown("---")
#
# # Session state initialization
# if "chat" not in st.session_state:
#     st.session_state.chat = []
# if "thinking" not in st.session_state:
#     st.session_state.thinking = False
#
# # Display chat history
# st.subheader("🗨️ Conversation")
# for sender, message in st.session_state.chat:
#     st.markdown(f"**{sender}**: {message}")
#
# if st.session_state.thinking:
#     st.markdown("**Bot**: 🤔 ...thinking")
#
# st.markdown("---")
#
# # --- Form: Text Input and Buttons ---
# with st.form(key="chat_form", clear_on_submit=True):
#     user_input = st.text_input("Type your message", key="input_box", label_visibility="collapsed")
#     col1, col2 = st.columns([1, 1])
#     with col1:
#         send_clicked = st.form_submit_button("Send")
#     with col2:
#         st.session_state.mic_clicked = st.form_submit_button("🎤")
#
# # --- Mic Click Handling ---
# if st.session_state.get("mic_clicked", False):
#     audio_bytes, transcribed_text = record_audio_sr()
#     st.session_state.chat.append(("You (voice)", transcribed_text))
#     st.session_state.audio_bytes = audio_bytes
#     st.session_state.from_voice = True
#     st.session_state.thinking = True
#     st.session_state.mic_clicked = False
#     st.rerun()
#
# # --- Text Input Handling ---
# if send_clicked and user_input.strip():
#     st.session_state.chat.append(("You (text)", user_input.strip()))
#     st.session_state.thinking = True
#     st.rerun()
#
# # --- Bot Response Handler ---
# if st.session_state.thinking:
#     if st.session_state.get("from_voice", False):
#         result = detect_intent_audio(st.session_state.audio_bytes)
#         st.session_state.from_voice = False
#     else:
#         result = detect_intent_text(st.session_state.chat[-1][1])
#
#     st.session_state.chat.append(("Bot", result.fulfillment_text))
#     st.session_state.thinking = False
#     speak(result.fulfillment_text)
#     st.rerun()
