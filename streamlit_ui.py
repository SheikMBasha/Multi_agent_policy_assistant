import os
import streamlit as st
from google.cloud import dialogflow_v2 as dialogflow

# Set path to your service account key
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "D:\\LearningWorkSpace\\AIVoiceAssistant\\autovoiceassistant-ontd-6d4a215489f5.json"

# Dialogflow settings
PROJECT_ID = "autovoiceassistant-ontd"
SESSION_ID = "streamlit-session-1"
LANGUAGE_CODE = "en"

st.title("💬 AI Voice Assistant (via Dialogflow)")

user_input = st.text_input("🗣️ Ask me anything:")

if st.button("Send") and user_input:
    session_client = dialogflow.SessionsClient()
    session_path = session_client.session_path(PROJECT_ID, SESSION_ID)

    text_input = dialogflow.TextInput(text=user_input, language_code=LANGUAGE_CODE)
    query_input = dialogflow.QueryInput(text=text_input)

    with st.spinner("Contacting your AI assistant..."):
        response = session_client.detect_intent(request={"session": session_path, "query_input": query_input})

        fulfillment = response.query_result.fulfillment_text
        st.markdown("### 🤖 Response:")
        st.markdown(fulfillment)