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

# This is a preview version of Lyria3 custom nodes

import base64
import io
import wave
from typing import Any, Dict, Optional

import numpy as np
import torch
from google import genai
from google.genai import types

from .base import VertexAIClient
from .constants import LYRIA3_USER_AGENT, Lyria3Model
from .custom_exceptions import APIExecutionError, ConfigurationError
from .logger import get_node_logger
from .retry import api_error_retry

logger = get_node_logger(__name__)


class Lyria3API(VertexAIClient):
    """
    A class to interact with the Google Lyria 3 and Lyria 3 Pro APIs for music generation.
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
            user_agent=LYRIA3_USER_AGENT,
            api_key=api_key,
        )

    @api_error_retry
    def generate_music(
        self,
        model: str,
        prompt: str,
    ) -> Dict[str, Any]:
        """Generates music using Lyria 3 models from a text prompt."""
        model_enum = Lyria3Model[model]

        try:
            stream = self.client.interactions.create(
                model=model_enum.value,
                input=prompt,
                stream=True,
            )
            
            audio_bytes = b""
            for event in stream:
                if event.event_type == "content.delta":
                    if event.delta.type == "audio":
                        audio_bytes += base64.b64decode(event.delta.data)
            
            if not audio_bytes:
                raise APIExecutionError("No audio data returned from Lyria 3.")
                
            return self._bytes_to_comfy_audio(audio_bytes)
            
        except Exception as e:
            raise APIExecutionError(f"Lyria 3 generation failed: {e}") from e

    @api_error_retry
    def generate_music_from_image(
        self,
        model: str,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/png"
    ) -> Dict[str, Any]:
        """Generates music using Lyria 3 models based on a multimodal prompt (image + text)."""
        model_enum = Lyria3Model[model]
        
        try:
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            input_data = [
                {"type": "text", "text": prompt},
                {"type": "image", "mime_type": mime_type, "data": base64_image}
            ]
            
            stream = self.client.interactions.create(
                model=model_enum.value,
                input=input_data,
                stream=True,
            )
            
            audio_bytes = b""
            for event in stream:
                if event.event_type == "content.delta":
                    if event.delta.type == "audio":
                        audio_bytes += base64.b64decode(event.delta.data)
            
            if not audio_bytes:
                raise APIExecutionError("No audio data returned from Lyria 3 multimodal prompt.")
                
            return self._bytes_to_comfy_audio(audio_bytes)
            
        except Exception as e:
            raise APIExecutionError(f"Lyria 3 image-to-music generation failed: {e}") from e

    def _bytes_to_comfy_audio(self, audio_bytes: bytes) -> Dict[str, Any]:
        """Converts raw audio bytes (MP3/WAV) to ComfyUI audio format using torchaudio."""
        import torchaudio
        import tempfile
        import os

        # Write bytes to a temporary file since torchaudio.load is more reliable with file paths
        # than with BytesIO (especially for compressed formats like MP3 on some backends)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        try:
            waveform, sample_rate = torchaudio.load(tmp_path)
            # torchaudio loads as (Channels, Samples). ComfyUI expects (Batch, Channels, Samples)
            return {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
        except Exception as e:
            raise APIExecutionError(f"Failed to decode audio response with torchaudio: {e}") from e
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
