import spacy
from datetime import datetime, timedelta
import re
import json
import logging
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class NERExtractor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(logging.StreamHandler())
        self.logger.info("Initializing NERExtractor")
        self.nlp = spacy.load("en_core_web_sm")
        self.client_secret_path = "/Users/nileshhanotia/Desktop/MLC/voice_agent_1/client_secret.json"

    def extract_entities(self, text):
        try:
            self.logger.info(f"Extracting entities from text: {text}")
            doc = self.nlp(text)
            entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents if ent.label_ in {"DATE", "TIME", "PERSON", "PHONE"}]
            self.logger.info(f"Extracted entities: {entities}")
            return entities
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return []

    def parse_details(self, entities):
        date = None
        time = None
        name = None
        phone = None

        for entity in entities:
            if entity['label'] == 'DATE':
                date = entity['text']
            elif entity['label'] == 'TIME':
                time = entity['text']
            elif entity['label'] == 'PERSON':
                name = entity['text']
            elif entity['label'] == 'PHONE':
                phone = entity['text']

        self.logger.info(f"Parsed date: {date}, time: {time}, name: {name}, phone: {phone}")

        if date and time:
            try:
                # Preprocess date string
                date = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date)
                # Combine date and time strings
                datetime_str = f"{date} {time}"
                # Parse datetime
                start_time = datetime.strptime(datetime_str, "%B %d %Y %I:%M %p")
                end_time = start_time + timedelta(hours=1)
                self.logger.info(f"Parsed datetime: start_time={start_time}, end_time={end_time}")
                return {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "name": name,
                    "phone": phone
                }
            except ValueError as e:
                self.logger.error(f"Failed to parse datetime: {e}")
        else:
            self.logger.error("Failed to parse date and time")
        return {"start_time": None, "end_time": None, "name": name, "phone": phone}

    def entities_to_json(self, entities):
        try:
            entities_json = json.dumps(entities, indent=4)
            self.logger.info(f"Entities JSON: {entities_json}")
            return entities_json
        except Exception as e:
            self.logger.error(f"Error converting entities to JSON: {e}")
            return "{}"
    
    def create_google_calendar_event(self, event_details):
        try:
            # Authenticate using client secret JSON file
            credentials = self.get_credentials()
            if not credentials:
                self.logger.error("Failed to obtain credentials")
                return False

            # Construct event data
            event_data = {
                'summary': 'Meeting',  # Event summary
                'description': 'Appointment with ' + event_details['name'],  # Event description
                'start': {'dateTime': event_details['start_time']},  # Event start time
                'end': {'dateTime': event_details['end_time']},  # Event end time
            }

            # Create Google Calendar API service
            service = build('calendar', 'v3', credentials=credentials)

            # Send POST request to Google Calendar API to create event
            response = service.events().insert(calendarId='primary', body=event_data).execute()

            if response.get('id'):
                self.logger.info("Event created successfully")
                return True
            else:
                self.logger.error("Failed to create event")
                return False
        except Exception as e:
            self.logger.error(f"Error creating event: {e}")
            return False

    def get_credentials(self):
        try:
            if os.path.exists(self.client_secret_path):
                flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_path, ['https://www.googleapis.com/auth/calendar'])
                credentials = flow.run_local_server(port=0)
                return credentials
            else:
                self.logger.error("Client secret JSON file not found")
                return None
        except Exception as e:
            self.logger.error(f"Error obtaining credentials: {e}")
            return None

    def send_confirmation_message(self):
        try:
            confirmation_text = "Your meeting has been confirmed."
            tts = gTTS(text=confirmation_text, lang='en')
            tts.save("confirmation.mp3")
            # Play confirmation message using command prompt
            subprocess.run(["afplay", "confirmation.mp3"])
        except Exception as e:
            self.logger.error(f"Error sending confirmation message: {e}")

# Example usage
if __name__ == "__main__":
    extractor = NERExtractor()
    extractor.send_confirmation_message()


