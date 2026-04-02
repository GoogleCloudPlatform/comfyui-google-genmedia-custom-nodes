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

from typing import Any, Dict, Optional, Tuple

from .constants import CHIRP3_HD_VOICES, GEMINI_TTS_VOICES, TTSModel
from .tts_api import TTSAPI


class GeminiTTSNode:
    """
    ComfyUI node — Gemini Text-to-Speech.

    Uses the Cloud TTS API with a Gemini TTS model (gemini-2.5-flash-tts or
    gemini-2.5-pro-tts). Voice names are bare identifiers such as "Kore" or "Puck".
    See: https://cloud.google.com/text-to-speech/docs/gemini-tts
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello, how are you today?"}),
                "model": ([m.name for m in TTSModel], {"default": TTSModel.GEMINI_TTS_FLASH.name}),
                "voice_name": (GEMINI_TTS_VOICES, {"default": "Kore"}),
                "language_code": ("STRING", {"default": "en-US"}),
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
        voice_name: str,
        language_code: str,
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any],]:
        try:
            api = TTSAPI(
                project_id=gcp_project_id or None,
                region=gcp_region or None,
                api_key=api_key or None,
            )
            audio_data = api.generate_speech_gemini(
                model=model,
                text=text,
                voice_name=voice_name,
                language_code=language_code,
            )
            return (audio_data,)
        except Exception as e:
            raise RuntimeError(f"Gemini TTS generation failed: {e}") from e


class GeminiTTSEnhanced:
    """
    ComfyUI node — Gemini TTS with style prompt.

    The style_prompt field maps to the Cloud TTS `prompt` parameter, which
    accepts natural language style instructions and markup tags:
      [sigh], [laughing], [uhm], [whispering], [shouting], [sarcasm],
      [short pause], [medium pause], [long pause], [extremely fast], [robotic]

    See: https://cloud.google.com/text-to-speech/docs/gemini-tts
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello, how are you today?"}),
                "model": ([m.name for m in TTSModel], {"default": TTSModel.GEMINI_TTS_FLASH.name}),
                "voice_name": (GEMINI_TTS_VOICES, {"default": "Kore"}),
                "language_code": ("STRING", {"default": "en-US"}),
                "style_prompt": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "e.g. Speak in a warm, friendly tone. [medium pause] Add emphasis on key words.",
                    },
                ),
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
        voice_name: str,
        language_code: str,
        style_prompt: str = "",
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any],]:
        try:
            api = TTSAPI(
                project_id=gcp_project_id or None,
                region=gcp_region or None,
                api_key=api_key or None,
            )
            audio_data = api.generate_speech_gemini_enhanced(
                model=model,
                text=text,
                voice_name=voice_name,
                language_code=language_code,
                style_prompt=style_prompt,
            )
            return (audio_data,)
        except Exception as e:
            raise RuntimeError(f"Gemini TTS Enhanced generation failed: {e}") from e


class Chirp3HDTTSNode:
    """
    ComfyUI node — Chirp 3 HD Text-to-Speech.

    Uses the Cloud TTS API with Chirp 3 HD voices (en-US-Chirp3-HD-*).
    Supports speaking_rate control (0.25–2.0) and [pause short/long] markup.
    See: https://cloud.google.com/text-to-speech/docs/chirp3-hd
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Hello, how are you today?"}),
                "voice_name": (CHIRP3_HD_VOICES, {"default": "en-US-Chirp3-HD-Charon"}),
                "language_code": ("STRING", {"default": "en-US"}),
                "speaking_rate": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.25, "max": 2.0, "step": 0.05},
                ),
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
        voice_name: str,
        language_code: str,
        speaking_rate: float = 1.0,
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any],]:
        try:
            api = TTSAPI(
                project_id=gcp_project_id or None,
                region=gcp_region or None,
                api_key=api_key or None,
            )
            audio_data = api.generate_speech_chirp3_hd(
                text=text,
                voice_name=voice_name,
                language_code=language_code,
                speaking_rate=speaking_rate,
            )
            return (audio_data,)
        except Exception as e:
            raise RuntimeError(f"Chirp 3 HD TTS generation failed: {e}") from e


NODE_CLASS_MAPPINGS = {
    "GeminiTTSNode": GeminiTTSNode,
    "GeminiTTSEnhanced": GeminiTTSEnhanced,
    "Chirp3HDTTSNode": Chirp3HDTTSNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GeminiTTSNode": "Gemini Text To Speech",
    "GeminiTTSEnhanced": "Gemini TTS Enhanced (with Style Prompt)",
    "Chirp3HDTTSNode": "Chirp 3 HD Text To Speech",
}
