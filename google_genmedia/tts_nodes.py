# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This is a preview version of TTS custom nodes

from typing import Any, Dict, Optional, Tuple

from .constants import SpeechModel, TTSModel
from .custom_exceptions import ConfigurationError
from .tts_api import TTSAPI


class GeminiTTSNode:
    """
    A ComfyUI node for generating speech from text using Gemini 2.0.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello, how are you today?"}),
                "model": ([m.name for m in TTSModel], {"default": TTSModel.GEMINI_TTS_FLASH.name}),
                "voice_id": (["Puck", "Charon", "Kore", "Fenrir", "Aoede"], {"default": "Puck"}),
            },
            "optional": {
                "api_key": ("STRING", {"default": ""}),
                "gcp_project_id": ("STRING", {"default": ""}),
                "gcp_region": ("STRING", {"default": "us-central1"}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate"
    CATEGORY = "Google AI/TTS"

    def generate(
        self,
        text: str,
        model: str,
        voice_id: str,
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any],]:
        try:
            init_api_key = api_key if api_key else None
            api = TTSAPI(project_id=gcp_project_id, region=gcp_region, api_key=init_api_key)
            audio_data = api.generate_speech_gemini(model=model, text=text, voice_id=voice_id)
            return (audio_data,)
        except Exception as e:
            raise RuntimeError(f"Gemini TTS generation failed: {e}")


class ChirpTTSNode:
    """
    A ComfyUI node for generating speech from text using Chirp.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello, how are you today?"}),
                "model": ([m.name for m in SpeechModel], {"default": SpeechModel.CHIRP_2.name}),
            },
            "optional": {
                "api_key": ("STRING", {"default": ""}),
                "gcp_project_id": ("STRING", {"default": ""}),
                "gcp_region": ("STRING", {"default": "us-central1"}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate"
    CATEGORY = "Google AI/TTS"

    def generate(
        self,
        text: str,
        model: str,
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any],]:
        try:
            init_api_key = api_key if api_key else None
            api = TTSAPI(project_id=gcp_project_id, region=gcp_region, api_key=init_api_key)
            audio_data = api.generate_speech_chirp(model=model, text=text)
            return (audio_data,)
        except Exception as e:
            raise RuntimeError(f"Chirp TTS generation failed: {e}")


class GeminiTTSEnhanced:
    """
    A ComfyUI node for generating enhanced speech from text using Gemini models with emotion and style control.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello, how are you today?"}),
                "model": ([m.name for m in TTSModel], {"default": TTSModel.GEMINI_TTS_FLASH.name}),
                "voice_id": (["Puck", "Charon", "Kore", "Fenrir", "Aoede"], {"default": "Puck"}),
                "emotion": (["none", "anger", "joy", "empathy"], {"default": "none"}),
                "style": ("STRING", {"default": "none"}),
            },
            "optional": {
                "api_key": ("STRING", {"default": ""}),
                "gcp_project_id": ("STRING", {"default": ""}),
                "gcp_region": ("STRING", {"default": "us-central1"}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate"
    CATEGORY = "Google AI/TTS"

    def generate(
        self,
        text: str,
        model: str,
        voice_id: str,
        emotion: str = "none",
        style: str = "none",
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any],]:
        try:
            init_api_key = api_key if api_key else None
            api = TTSAPI(project_id=gcp_project_id, region=gcp_region, api_key=init_api_key)
            audio_data = api.generate_speech_gemini_enhanced(model=model, text=text, voice_id=voice_id, emotion=emotion, style=style)
            return (audio_data,)
        except Exception as e:
            raise RuntimeError(f"Gemini Enhanced TTS generation failed: {e}")


class Chirp3TTSWithCloning:
    """
    A ComfyUI node for generating speech from text using Chirp 3 with voice cloning.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello, how are you today?"}),
                "model": ([m.name for m in SpeechModel], {"default": SpeechModel.CHIRP_3.name}),
                "reference_audio": ("AUDIO",),
            },
            "optional": {
                "api_key": ("STRING", {"default": ""}),
                "gcp_project_id": ("STRING", {"default": ""}),
                "gcp_region": ("STRING", {"default": "us-central1"}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate"
    CATEGORY = "Google AI/TTS"

    def generate(
        self,
        text: str,
        model: str,
        reference_audio: dict,
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any],]:
        try:
            init_api_key = api_key if api_key else None
            api = TTSAPI(project_id=gcp_project_id, region=gcp_region, api_key=init_api_key)
            audio_data = api.generate_speech_chirp_cloning(model=model, text=text, reference_audio=reference_audio)
            return (audio_data,)
        except Exception as e:
            raise RuntimeError(f"Chirp 3 TTS with cloning failed: {e}")


NODE_CLASS_MAPPINGS = {
    "GeminiTTSNode": GeminiTTSNode,
    "ChirpTTSNode": ChirpTTSNode,
    "GeminiTTSEnhanced": GeminiTTSEnhanced,
    "Chirp3TTSWithCloning": Chirp3TTSWithCloning,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GeminiTTSNode": "Gemini 2.0 Text To Speech",
    "ChirpTTSNode": "Chirp Text To Speech",
    "GeminiTTSEnhanced": "Gemini TTS Enhanced",
    "Chirp3TTSWithCloning": "Chirp 3 TTS With Cloning",
}
