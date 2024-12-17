# google_calendar_manager.py
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

class GoogleCalendarScheduler:
    def __init__(self, credentials_path):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.creds = None
        self.credentials_path = credentials_path
        self.service = None

    def authenticate(self):
        if self.creds and self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.SCOPES)
            self.creds = flow.run_local_server(port=0)
        self.service = build('calendar', 'v3', credentials=self.creds)

    async def create_event(self, event):
        if not self.service:
            self.authenticate()
        return self.service.events().insert(calendarId='primary', body=event).execute()

    async def update_event(self, event_id, event):
        if not self.service:
            self.authenticate()
        return self.service.events().update(calendarId='primary', eventId=event_id, body=event).execute()

    async def delete_event(self, event_id):
        if not self.service:
            self.authenticate()
        return self.service.events().delete(calendarId='primary', eventId=event_id).execute()

    async def search_events(self, name, date, time):
        if not self.service:
            self.authenticate()
        time_min = f"{date}T{time}:00-07:00"
        time_max = f"{date}T23:59:59-07:00"
        events_result = self.service.events().list(calendarId='primary', timeMin=time_min,
                                                   timeMax=time_max, singleEvents=True,
                                                   orderBy='startTime').execute()
        events = events_result.get('items', [])
        return [event for event in events if name.lower() in event['summary'].lower()]

    async def check_availability(self, date, time):
        if not self.service:
            self.authenticate()
        time_min = f"{date}T{time}:00-07:00"
        time_max = f"{date}T{time}:30-07:00"  # Assuming 30-minute appointments
        events_result = self.service.events().list(calendarId='primary', timeMin=time_min,
                                                   timeMax=time_max, singleEvents=True,
                                                   orderBy='startTime').execute()
        events = events_result.get('items', [])
        return len(events) == 0