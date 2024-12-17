# Standard library imports
import asyncio
import json
import os
import logging

# FastAPI and Starlette imports
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.websockets import WebSocketDisconnect

# Application imports
from api.utils.language_processor import LanguageModelProcessor
from api.utils.text_to_speech import TextToSpeech
from api.utils.transcript_collector import TranscriptCollector
from api.utils.ner_extractor import NERExtractor
from api.utils.calendar_manager import GoogleCalendarScheduler


# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New client connected")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Client disconnected")

manager = ConnectionManager()

class ConversationState:
    def __init__(self):
        self.state = "greeting"
        self.patient_info = {}
        self.is_booking_appointment = False

@app.get("/")
async def root():
    return FileResponse("index.html")
    
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    conversation_state = ConversationState()
    
    try:
        while True:
            try:
                # Receive and parse the message
                data = await websocket.receive_text()
                logger.info(f"Received message: {data[:100]}...")  # Log first 100 chars
                message = json.loads(data)
                
                if message["type"] == "transcription":
                    transcription = message["text"]
                    
                    # Process the conversation
                    response = await process_conversation(transcription, conversation_state)
                    logger.info(f"Generated response: {response[:100]}...")  # Log first 100 chars
                    
                    try:
                        # Get audio response
                        audio_data = await tts.speak(response)
                        
                        # Convert audio data to base64 if it's bytes
                        if isinstance(audio_data, bytes):
                            audio_data = base64.b64encode(audio_data).decode('utf-8')
                        
                        # Send response
                        await websocket.send_json({
                            "type": "response",
                            "text": response,
                            "audio": audio_data
                        })
                        logger.info("Response sent successfully")
                        
                    except Exception as audio_error:
                        logger.error(f"Audio processing error: {audio_error}")
                        await websocket.send_json({
                            "type": "response",
                            "text": response,
                            "error": "Audio generation failed"
                        })
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message format"
                })
                continue
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)

async def process_conversation(transcription: str, state: ConversationState) -> str:
    """Process conversation and return appropriate response."""
    try:
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
    except Exception as e:
        logger.error(f"Error processing conversation: {e}")
        return "I apologize, but I'm having trouble processing your request. Could you please try again?"

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
            state.is_booking_appointment = False
            state.state = "listening"
            return f"Great! I've noted your preferred time. We'll verify availability and contact you to confirm the appointment. Is there anything else I can help you with?"
        except Exception as e:
            logger.error(f"Appointment booking error: {e}")
            return "I apologize, but I'm having trouble scheduling the appointment. Could you please try again or call our office directly?"
    
    return "I apologize, but I'm having trouble with your request. Could you please repeat that?"

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
