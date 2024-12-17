import requests
import base64
import logging

class TextToSpeech:
    def __init__(self, api_key):
        self.api_key = api_key
        self.model_name = "aura-helios-en"
        self.logger = logging.getLogger(__name__)

    def speak(self, text):
        try:
            url = "https://api.deepgram.com/v1/speak"
            params = {
                "model": self.model_name,
                "encoding": "linear16",
                "sample_rate": 16000,
            }
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "text": text
            }

            response = requests.post(url, params=params, headers=headers, json=payload)

            if response.status_code == 200:
                # Convert the audio data to base64
                audio_base64 = base64.b64encode(response.content).decode('utf-8')
                return audio_base64
            else:
                self.logger.error(f"Deepgram API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Error in text_to_speech: {e}")
            return None
