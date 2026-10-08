"""
Abstract Base Provider for Voice & Audio integrations.
Enables provider-agnostic voice architecture (Retell AI, Bolna, Browser Web Speech, local TTS).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, AsyncGenerator


class VoiceProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier name of the voice provider."""
        pass

    @abstractmethod
    async def synthesize_speech(self, text: str, language: str = "English", voice_id: Optional[str] = None) -> bytes:
        """Synthesizes text into audio bytes (e.g. mp3/wav)."""
        pass

    @abstractmethod
    async def transcribe_audio(self, audio_bytes: bytes, language: str = "English") -> str:
        """Transcribes incoming audio bytes into text."""
        pass

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Returns configuration metadata for the provider."""
        pass
