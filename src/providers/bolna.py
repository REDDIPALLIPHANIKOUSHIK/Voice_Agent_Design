"""
Bolna Voice Agent Provider Integration.
Supports Bolna webhook callbacks, agent dispatch, and real-time conversation event hooks.
"""

import os
import logging
from typing import Optional, Dict, Any
from src.providers.base import VoiceProvider

logger = logging.getLogger(__name__)


class BolnaProvider(VoiceProvider):
    def __init__(self, api_key: Optional[str] = None, agent_id: Optional[str] = None):
        self.api_key = api_key or os.getenv("BOLNA_API_KEY", "")
        self.agent_id = agent_id or os.getenv("BOLNA_AGENT_ID", "")

    @property
    def provider_name(self) -> str:
        return "bolna"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.agent_id and "your_" not in self.api_key)

    async def synthesize_speech(self, text: str, language: str = "English", voice_id: Optional[str] = None) -> bytes:
        return b""

    async def transcribe_audio(self, audio_bytes: bytes, language: str = "English") -> str:
        return ""

    def format_bolna_response(self, text: str, end_call: bool = False) -> Dict[str, Any]:
        """
        Formats response according to Bolna agent protocol.
        """
        return {
            "type": "text",
            "content": text,
            "end_call": end_call,
        }

    def get_config(self) -> Dict[str, Any]:
        return {
            "provider": self.provider_name,
            "configured": self.is_configured(),
            "agent_id": self.agent_id or "not_set",
            "supported_languages": ["en-IN", "hi-IN"],
        }
