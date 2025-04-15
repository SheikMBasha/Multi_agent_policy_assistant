import pyttsx3
import re


class ResponseHandler:
    def __init__(self):
        self.engine = pyttsx3.init()

        # Get available voices and set the best available one
        voices = self.engine.getProperty('voices')

        for voice in voices:
            print(f"Voice ID: {voice.id}")
            print(f"Voice Name: {voice.name}")
            print(f"Voice Languages: {voice.languages}")
            print("------------------------")

        # Try to find US English voice
        us_voice = next((voice for voice in voices if 'en-us' in voice.languages), None)
        if us_voice:
            self.engine.setProperty('voice', us_voice.id)
            print(f"Using US English voice: {us_voice.name}")
        elif voices:
            self.engine.setProperty('voice', voices[0].id)
            print(f"Using default voice: {voices[0].name}")

        # Optimize speech parameters
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)
        self.engine.setProperty('pitch', 100)

    def clean_text(self, text):
        """Remove special characters that cause speech issues."""
        text = re.sub(r'[*`#@$%^&+=<>~|]', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('...', '.')
        text = re.sub(r'\.+', '.', text)
        text = re.sub(r'!+', '!', text)
        text = re.sub(r'\?+', '?', text)
        return text.strip()

    def speak(self, text):
        """Convert text to speech, supports optional [PAUSE] marker to break into two parts."""
        print(f"🔊 Speaking: {text}")
        cleaned_text = self.clean_text(text)

        # Split on custom pause token
        if "[PAUSE]" in cleaned_text:
            parts = cleaned_text.split("[PAUSE]")
        elif "|" in cleaned_text:  # Optional fallback
            parts = cleaned_text.split("|")
        else:
            parts = [cleaned_text]

        # Speak each part with a pause in between
        for part in parts:
            part = part.strip()
            if part:
                self.engine.say(part)
                self.engine.runAndWait()
