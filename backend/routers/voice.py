from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
import io
from shared import db, now_iso, log_operation, logger, EMERGENT_KEY, stt_client, eleven_client, VoiceSettings

router = APIRouter(prefix="/api")

class TTSRequest(BaseModel):
    text: str
    voice_id: str = "JBFqnCBsd6RMkjVDRZzb"

@router.post("/voice/transcribe")
async def transcribe_audio(audio_file: UploadFile = File(...)):
    if not stt_client:
        raise HTTPException(status_code=500, detail="STT not configured")
    try:
        audio_content = await audio_file.read()
        audio_io = io.BytesIO(audio_content)
        audio_io.name = audio_file.filename or "audio.webm"
        response = await stt_client.transcribe(file=audio_io, model="whisper-1", response_format="json")
        text = response.text if hasattr(response, 'text') else str(response)
        await log_operation("VOICE_TRANSCRIBE", "Whisper", f"Transcribed: {text[:50]}...", "SUCCESS")
        return {"text": text}
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@router.post("/voice/speak")
async def text_to_speech(request: TTSRequest):
    if not eleven_client:
        raise HTTPException(status_code=500, detail="TTS not configured")
    try:
        import base64
        audio_generator = eleven_client.text_to_speech.convert(
            text=request.text[:5000], voice_id=request.voice_id, model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.0, use_speaker_boost=True)
        )
        audio_data = b""
        for chunk in audio_generator:
            audio_data += chunk
        audio_b64 = base64.b64encode(audio_data).decode()
        await log_operation("VOICE_SPEAK", "ElevenLabs", f"Generated speech: {request.text[:50]}...", "SUCCESS")
        return {"audio": f"data:audio/mpeg;base64,{audio_b64}"}
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

@router.get("/voice/voices")
async def get_voices():
    default_voices = [
        {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "name": "George", "category": "premade"},
        {"voice_id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "category": "premade"},
        {"voice_id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "category": "premade"},
        {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "category": "premade"},
        {"voice_id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "category": "premade"},
        {"voice_id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "category": "premade"},
        {"voice_id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "category": "premade"},
        {"voice_id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "category": "premade"},
    ]
    if not eleven_client:
        return default_voices
    try:
        voices_response = eleven_client.voices.get_all()
        return [{"voice_id": v.voice_id, "name": v.name, "category": getattr(v, 'category', 'unknown')} for v in voices_response.voices[:20]]
    except Exception as e:
        logger.warning(f"Get voices fallback to defaults: {e}")
        return default_voices
