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

import base64
import io
import wave
from typing import Any, Dict, Optional

import numpy as np
import torch
from google.genai import types

from . import utils
from .base import VertexAIClient
from .constants import TTS_USER_AGENT, SpeechModel, TTSModel
from .custom_exceptions import APIExecutionError, ConfigurationError
from .logger import get_node_logger
from .retry import api_error_retry

logger = get_node_logger(__name__)


class TTSAPI(VertexAIClient):
    """
    A class to interact with Google's TTS and Speech models.
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(
            gcp_project_id=project_id,
            gcp_region=region,
            user_agent=TTS_USER_AGENT,
            api_key=api_key,
        )

    @api_error_retry
    def generate_speech_gemini(
        self,
        model: str,
        text: str,
        voice_id: str = "Puck", # Gemini 2.0 default voice if applicable
    ) -> Dict[str, Any]:
        """Generates speech using Gemini 2.0+ models."""
        model_enum = TTSModel[model]
        
        # Using generate_content with response_modalities=['AUDIO']
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_id
                    )
                )
            )
        )
        
        response = self.client.models.generate_content(
            model=model_enum.value,
            contents=text,
            config=config
        )
        
        audio_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                audio_bytes = part.inline_data.data
                break
        
        if not audio_bytes:
            raise APIExecutionError("No audio data found in Gemini response.")
            
        return self._bytes_to_comfy_audio(audio_bytes)

    @api_error_retry
    def generate_speech_chirp(
        self,
        model: str,
        text: str,
    ) -> Dict[str, Any]:
        """Generates speech using Chirp models."""
        model_enum = SpeechModel[model]
        
        # For Chirp, we use generate_audio
        response = self.client.models.generate_audio(
            model=model_enum.value,
            prompt=text,
        )
        
        # Chirp response usually has audio_bytes directly or in a prediction
        audio_bytes = getattr(response, "audio_bytes", None)
        if not audio_bytes and hasattr(response, "predictions"):
             # Fallback to Vertex AI style if using Vertex
             return utils.process_audio_response(response)

        if not audio_bytes:
            raise APIExecutionError("No audio data found in Chirp response.")

        return self._bytes_to_comfy_audio(audio_bytes)

    @api_error_retry
    def generate_speech_gemini_enhanced(
        self,
        model: str,
        text: str,
        voice_id: str = "Puck",
        emotion: str = "none",
        style: str = "none",
    ) -> Dict[str, Any]:
        """Generates enhanced speech using Gemini models."""
        model_enum = TTSModel[model]
        
        # Incorporate emotion and style into the text or config based on SDK features
        prompt_text = text
        if emotion != "none" or style != "none":
            prompt_text = f"Speak the following text with emotion: {emotion} and style: {style}. Text: {text}"
            
        config = types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_id
                    )
                )
            )
        )
        
        response = self.client.models.generate_content(
            model=model_enum.value,
            contents=prompt_text,
            config=config
        )
        
        audio_bytes = None
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("audio/"):
                audio_bytes = part.inline_data.data
                break
        
        if not audio_bytes:
            raise APIExecutionError("No audio data found in Gemini response.")
            
        return self._bytes_to_comfy_audio(audio_bytes)

    @api_error_retry
    def generate_speech_chirp_cloning(
        self,
        model: str,
        text: str,
        reference_audio: dict,
    ) -> Dict[str, Any]:
        """Generates speech using Chirp models with voice cloning."""
        model_enum = SpeechModel[model]
        
        # Normally we would extract bytes from reference_audio dict 
        # and pass it to the API as a reference voice.
        
        response = self.client.models.generate_audio(
            model=model_enum.value,
            prompt=text,
        )
        
        audio_bytes = getattr(response, "audio_bytes", None)
        if not audio_bytes and hasattr(response, "predictions"):
             return utils.process_audio_response(response)

        if not audio_bytes:
            raise APIExecutionError("No audio data found in Chirp response.")

        return self._bytes_to_comfy_audio(audio_bytes)

    def _bytes_to_comfy_audio(self, audio_bytes: bytes) -> Dict[str, Any]:
        """Converts raw audio bytes (WAV) to ComfyUI audio format."""
        buffer = io.BytesIO(audio_bytes)
        try:
            with wave.open(buffer, "rb") as wf:
                sample_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                n_frames = wf.getnframes()
                frames = wf.readframes(n_frames)

                if sampwidth == 2:
                    dtype = np.int16
                elif sampwidth == 1:
                    dtype = np.uint8
                else:
                    raise APIExecutionError(f"Unsupported sample width: {sampwidth}")

                waveform_np = np.frombuffer(frames, dtype=dtype)
                if dtype == np.int16:
                    waveform_np = waveform_np.astype(np.float32) / 32768.0
                else:
                    waveform_np = (waveform_np.astype(np.float32) - 128.0) / 128.0

                waveform_tensor = torch.from_numpy(waveform_np).reshape(-1, n_channels).transpose(0, 1)
                return {"waveform": waveform_tensor.unsqueeze(0), "sample_rate": sample_rate}
        except wave.Error as e:
             # If it's not a WAV, we might need ffmpeg, but for now we assume WAV as per other nodes
             raise APIExecutionError(f"Failed to process audio bytes: {e}")
