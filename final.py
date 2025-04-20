import os
import streamlit as st
import speech_recognition as sr
from google.cloud import dialogflow_v2 as dialogflow
from google.cloud.dialogflow_v2.types import InputAudioConfig, QueryInput, AudioEncoding, TextInput

# Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"D:\LearningWorkSpace\AIVoiceAssistant\intelligent-ivr-jiud-fdd92f56d16f.json"

project_id = "intelligent-ivr-jiud"
session_id = "user-session-1"
language_code = "en-in"

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

# Record with speech_recognition
def record_audio_sr():
    r = sr.Recognizer()
    with sr.Microphone(sample_rate=16000) as source:
        st.info("🎤 Listening... Speak now.")
        audio = r.listen(source)
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

# Display chat history
st.subheader("🗨️ Conversation")
for sender, message in st.session_state.chat:
    st.markdown(f"**{sender}**: {message}")

if st.session_state.thinking:
    st.markdown("**Bot**: 🤔 ...thinking")

st.markdown("---")

# --- Form: Text Input and Send Button ---
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your message", key="input_box", label_visibility="collapsed")
    col1, col2 = st.columns([1, 1])
    with col1:
        send_clicked = st.form_submit_button("Send")
    with col2:
        st.session_state.mic_clicked = st.form_submit_button("🎤")  # Track mic inside same row

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

    st.session_state.chat.append(("Bot", result.fulfillment_text))
    st.session_state.thinking = False
    st.rerun()
