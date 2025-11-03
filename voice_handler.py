import io
import base64
import logging
from typing import Optional, Dict, Any
import requests
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        self.whisper_api_url = "https://api.openai.com/v1/audio/transcriptions"
        self.tts_api_url = "https://api.openai.com/v1/audio/speech"
    
    async def speech_to_text(self, audio_data: bytes, language: str = "auto") -> Optional[str]:
        """Convert speech to text using OpenAI Whisper API"""
        try:
            headers = {
                "Authorization": f"Bearer {config.OPENAI_API_KEY}"
            }
            
            files = {
                "file": ("audio.wav", io.BytesIO(audio_data), "audio/wav"),
                "model": (None, "whisper-1"),
                "language": (None, language if language != "auto" else None)
            }
            
            response = requests.post(self.whisper_api_url, headers=headers, files=files)
            response.raise_for_status()
            
            result = response.json()
            transcribed_text = result.get("text", "")
            
            logger.info(f"Speech transcribed: {transcribed_text[:50]}...")
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Error in speech-to-text: {e}")
            return None
    
    async def text_to_speech(self, text: str, language: str = "en", voice: str = "alloy") -> Optional[bytes]:
        """Convert text to speech using OpenAI TTS API"""
        try:
            headers = {
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Map language codes to appropriate voices
            voice_mapping = {
                "hi": "nova",  # Hindi
                "ta": "shimmer",  # Tamil
                "en": "alloy",  # English
                "te": "echo",  # Telugu
                "bn": "fable",  # Bengali
                "mr": "onyx"   # Marathi
            }
            
            selected_voice = voice_mapping.get(language, "alloy")
            
            data = {
                "model": "tts-1",
                "input": text,
                "voice": selected_voice,
                "response_format": "mp3"
            }
            
            response = requests.post(self.tts_api_url, headers=headers, json=data)
            response.raise_for_status()
            
            audio_content = response.content
            logger.info(f"Text-to-speech generated for: {text[:30]}...")
            return audio_content
            
        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return None
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return {
            "en": "English",
            "hi": "हिंदी (Hindi)",
            "ta": "தமிழ் (Tamil)",
            "te": "తెలుగు (Telugu)",
            "bn": "বাংলা (Bengali)",
            "mr": "मराठी (Marathi)",
            "gu": "ગુજરાતી (Gujarati)",
            "kn": "ಕನ್ನಡ (Kannada)",
            "ml": "മലയാളം (Malayalam)",
            "or": "ଓଡ଼ିଆ (Odia)",
            "pa": "ਪੰਜਾਬੀ (Punjabi)",
            "ur": "اردو (Urdu)"
        }

# Global voice handler instance
voice_handler = VoiceHandler()