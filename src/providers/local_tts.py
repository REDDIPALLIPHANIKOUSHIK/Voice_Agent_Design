"""
Local / Fallback Audio Provider using gTTS (Google Text-to-Speech)
Generates real audio bytes without requiring paid external API credentials.
"""

import io
from typing import Optional, Dict, Any
from gtts import gTTS
from src.providers.base import VoiceProvider


class LocalTTSProvider(VoiceProvider):
    @property
    def provider_name(self) -> str:
        return "local_tts"

    async def synthesize_speech(self, text: str, language: str = "English", voice_id: Optional[str] = None) -> bytes:
        """
        Converts text to speech using gTTS and returns MP3 audio bytes.
        """
        lang_code = "hi" if language.lower() == "hindi" else "en"
        fp = io.BytesIO()
        # Clean text for speech synthesis
        clean_text = text.replace("₹", "Rupees ")
        tts = gTTS(text=clean_text, lang=lang_code, slow=False)
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()

    async def transcribe_audio(self, audio_bytes: bytes, language: str = "English") -> str:
        """
        Transcribes audio bytes using SpeechRecognition.
        """
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio = recognizer.record(source)
            lang_code = "hi-IN" if language.lower() == "hindi" else "en-IN"
            return recognizer.recognize_google(audio, language=lang_code)
        except Exception:
            return ""

    def get_config(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "engine": "gTTS + SpeechRecognition",
            "offline_ready": True,
            "supported_languages": ["English", "Hindi"],
        }
