from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio
from utils.language_processor import LanguageModelProcessor
from utils.text_to_speech import TextToSpeech
from utils.transcript_collector import TranscriptCollector
from utils.ner_extractor import NERExtractor
from utils.calendar_manager import GoogleCalendarScheduler
import logging
import os

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
llm_processor = LanguageModelProcessor()
tts = TextToSpeech(api_key=os.getenv("DEEPGRAM_API_KEY"))
ner_extractor = NERExtractor()
calendar_api = GoogleCalendarScheduler(os.getenv("GOOGLE_CALENDAR_CREDENTIALS"))
transcript_collector = TranscriptCollector()

class ConversationState:
    def __init__(self):
        self.state = "greeting"
        self.patient_info = {}
        self.is_booking_appointment = False

@app.get("/")
async def root():
    return FileResponse('static/index.html')

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conversation_state = ConversationState()
    
    try:
        while True:
            # Receive audio data from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "transcription":
                transcription = message["text"]
                response = await process_conversation(transcription, conversation_state)
                
                # Get audio response
                audio_data = tts.speak(response)
                
                # Send response back to client
                await websocket.send_json({
                    "type": "response",
                    "text": response,
                    "audio": audio_data
                })
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

async def process_conversation(transcription: str, state: ConversationState) -> str:
    """Process conversation and return appropriate response."""
    
    # Handle greeting
    if state.state == "greeting":
        state.state = "listening"
        return "Good morning! Thank you for calling Dr. Smith's office. How can I assist you today?"
    
    # Check for appointment booking intent
    if not state.is_booking_appointment and check_appointment_intent(transcription):
        state.is_booking_appointment = True
        state.state = "collecting_name"
        return "I'd be happy to help you book an appointment. Can I have your full name, please?"
    
    # Handle appointment booking flow
    if state.is_booking_appointment:
        return await handle_appointment_booking(transcription, state)
    
    # Handle general queries
    return llm_processor.process(transcription)

def check_appointment_intent(text: str) -> bool:
    """Check if text indicates appointment booking intent."""
    appointment_keywords = [
        "book", "schedule", "appointment", "see the doctor",
        "make an appointment", "book a time", "schedule a visit"
    ]
    return any(keyword in text.lower() for keyword in appointment_keywords)

async def handle_appointment_booking(text: str, state: ConversationState) -> str:
    """Handle the appointment booking process."""
    if state.state == "collecting_name":
        state.patient_info['name'] = text
        state.state = "collecting_contact"
        return "Thank you. Can I have your contact number, please?"
    
    elif state.state == "collecting_contact":
        state.patient_info['contact'] = text
        state.state = "understanding_needs"
        return "What is the reason for your visit?"
    
    elif state.state == "understanding_needs":
        state.patient_info['reason'] = text
        state.state = "checking_availability"
        return "When would you prefer to schedule your appointment?"
    
    elif state.state == "checking_availability":
        try:
            # Extract date/time entities
            entities = ner_extractor.extract_entities(text)
            appointment_time = process_appointment_time(entities)
            
            if appointment_time:
                # Create calendar event
                event = create_calendar_event(state.patient_info, appointment_time)
                await calendar_api.create_event(event)
                
                # Reset state
                state.is_booking_appointment = False
                state.state = "listening"
                
                return f"Great! I've booked your appointment for {appointment_time}. Please arrive 15 minutes early with your ID and insurance card."
            else:
                return "I couldn't understand the time you specified. Could you please provide the date and time again?"
            
        except Exception as e:
            logger.error(f"Appointment booking error: {e}")
            return "I apologize, but I'm having trouble scheduling the appointment. Please try again or call our office directly."
    
    return "I apologize, but I'm having trouble with your request. Could you please repeat that?"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)