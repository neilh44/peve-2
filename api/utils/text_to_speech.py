import requests
import subprocess
import os

class TextToSpeech:
    def __init__(self, api_key):
        self.api_key = api_key
        self.model_name = "aura-helios-en"

    def speak(self, text):
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
            with open('output.wav', 'wb') as f:
                f.write(response.content)
            # Use ffplay to play the sound file asynchronously
            subprocess.run(["ffplay", "-autoexit", "-nodisp", "output.wav"])
        else:
            raise Exception(f"Error with TTS: {response.text}")
