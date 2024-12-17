from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from api.utils.language_processor import LanguageModelProcessor
from api.utils.text_to_speech import TextToSpeech
from api.utils.transcript_collector import TranscriptCollector
from api.utils.ner_extractor import NERExtractor
from api.utils.calendar_manager import GoogleCalendarScheduler
import logging

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

@app.get("/")
async def root():
    return {"status": "healthy", "message": "Medical Office Virtual Assistant API is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    conversation_state = ConversationState()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "transcription":
                transcription = message["text"]
                response = await process_conversation(transcription, conversation_state)
                
                # Get audio response
                audio_data = tts.speak(response)
                
                await websocket.send_json({
                    "type": "response",
                    "text": response,
                    "audio": audio_data
                })
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

class ConversationState:
    def __init__(self):
        self.state = "greeting"
        self.patient_info = {}
        self.is_booking_appointment = False

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)