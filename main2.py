from google.cloud import dialogflow_v2 as dialogflow
from google.cloud.dialogflow_v2.types import InputAudioConfig, QueryInput, AudioEncoding
import os
import speech_recognition as sr
from response_handler import ResponseHandler

# Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"D:\LearningWorkSpace\AIVoiceAssistant\intelligent-ivr-jiud-fdd92f56d16f.json"

# Dialogflow setup
project_id = "intelligent-ivr-jiud"
session_id = "user-session-1"
language_code = "en-in"

def detect_intent_audio(project_id, session_id, audio_bytes, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    audio_config = InputAudioConfig(
        audio_encoding=AudioEncoding.AUDIO_ENCODING_LINEAR_16,
        language_code=language_code,
        sample_rate_hertz=16000
    )

    query_input = QueryInput(audio_config=audio_config)
    response_handler = ResponseHandler()

    response = session_client.detect_intent(
        request={
            "session": session,
            "query_input": query_input,
            "input_audio": audio_bytes
        }
    )
    response_handler.speak(response.query_result.fulfillment_text)
    return response.query_result

def record_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone(sample_rate=16000) as source:
        print("🎤 Listening (sending audio to Dialogflow)...")
        audio = recognizer.listen(source)

    return audio.get_wav_data()

# Main loop
while True:
    audio_data = record_audio()
    result = detect_intent_audio(project_id, session_id, audio_data, language_code)

    print(f"🤖 Dialogflow Response: {result.fulfillment_text}")
    if "exit" in result.query_text.lower():
        break
