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

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    return FileResponse('static/index.html')  # Changed to serve index.html

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection attempt...")
    try:
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        conversation_state = ConversationState()

        # Send initial greeting
        try:
            initial_response = {
                "type": "response",
                "text": "Good morning! Thank you for calling Dr. Smith's office. How can I assist you today?",
                "audio": None  # Initialize without audio first
            }
            
            try:
                initial_response["audio"] = tts.speak("Good morning! Thank you for calling Dr. Smith's office. How can I assist you today?")
            except Exception as audio_error:
                logger.error(f"Error generating audio: {audio_error}")
                # Continue without audio if there's an error
            
            await websocket.send_json(initial_response)
            
        except Exception as e:
            logger.error(f"Error sending initial greeting: {e}")
            return

        while True:
            try:
                data = await websocket.receive_text()
                logger.info(f"Received data: {data}")
                
                message = json.loads(data)
                
                if message["type"] == "transcription":
                    transcription = message["text"]
                    logger.info(f"Processing transcription: {transcription}")
                    
                    response = await process_conversation(transcription, conversation_state)
                    
                    response_data = {
                        "type": "response",
                        "text": response,
                        "audio": None
                    }
                    
                    try:
                        response_data["audio"] = tts.speak(response)
                    except Exception as audio_error:
                        logger.error(f"Error generating audio response: {audio_error}")
                        # Continue without audio if there's an error
                    
                    await websocket.send_json(response_data)
                    logger.info("Response sent successfully")
                
            except WebSocketDisconnect:
                logger.info("Client disconnected normally")
                break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "text": "I apologize, but there was an error processing your request."
                    })
                except:
                    break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during setup")
    except Exception as e:
        logger.error(f"WebSocket setup error: {e}")
    finally:
        logger.info("WebSocket connection terminated")
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
