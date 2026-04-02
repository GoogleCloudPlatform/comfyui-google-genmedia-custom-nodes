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

import io
import os
import wave
from typing import Any, Dict, Optional

import numpy as np
import torch

from .config import get_gcp_metadata
from .constants import TTSModel
from .custom_exceptions import APIExecutionError, ConfigurationError
from .logger import get_node_logger
from .retry import api_error_retry

logger = get_node_logger(__name__)


class TTSAPI:
    """
    Interacts with Google Cloud Text-to-Speech API.

    Supports:
      - Gemini TTS models (gemini-2.5-flash-tts, gemini-2.5-pro-tts, etc.)
        via VoiceSelectionParams.model_name
      - Chirp 3 HD voices (en-US-Chirp3-HD-*) via VoiceSelectionParams.name

    Authentication priority:
      1. api_key parameter (node input)
      2. GEMINI_API_KEY environment variable (.env)
      3. GCP project + ADC (Vertex AI / Application Default Credentials)
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        region: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        try:
            from google.cloud import texttospeech
            from google.api_core.client_options import ClientOptions
        except ImportError as e:
            raise ConfigurationError(
                "google-cloud-texttospeech is required. "
                "Run: pip install google-cloud-texttospeech"
            ) from e

        self._tts = texttospeech
        effective_api_key = api_key or os.environ.get("GEMINI_API_KEY")

        if effective_api_key:
            logger.info("Initializing Cloud TTS client with API Key.")
            try:
                self.client = texttospeech.TextToSpeechClient(
                    client_options=ClientOptions(api_key=effective_api_key)
                )
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to initialize Cloud TTS client with API Key: {e}"
                ) from e
            return

        # Fallback: Vertex AI / ADC
        self.project_id = (
            project_id
            or os.environ.get("GCP_PROJECT_ID")
            or get_gcp_metadata("project/project-id")
        )
        self.region = region or os.environ.get("GCP_REGION")
        if not self.region:
            zone_metadata = get_gcp_metadata("instance/zone")
            if zone_metadata:
                try:
                    zone_name = zone_metadata.split("/")[-1]
                    self.region = "-".join(zone_name.split("-")[:-1])
                except Exception:
                    self.region = "us-central1"
            else:
                self.region = "us-central1"

        if not self.project_id:
            raise ConfigurationError(
                "GCP Project ID is required. Set GCP_PROJECT_ID in .env or provide an api_key."
            )

        logger.info(
            f"Initializing Cloud TTS client for Vertex AI "
            f"(project={self.project_id}, region={self.region})."
        )
        try:
            api_endpoint = f"{self.region}-texttospeech.googleapis.com"
            self.client = texttospeech.TextToSpeechClient(
                client_options=ClientOptions(
                    api_endpoint=api_endpoint,
                    quota_project_id=self.project_id,
                )
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize Cloud TTS Vertex AI client: {e}"
            ) from e

    # ------------------------------------------------------------------
    # Gemini TTS  (gemini-2.5-flash-tts / gemini-2.5-pro-tts)
    # https://cloud.google.com/text-to-speech/docs/gemini-tts
    # ------------------------------------------------------------------

    @api_error_retry
    def generate_speech_gemini(
        self,
        model: str,
        text: str,
        voice_name: str = "Kore",
        language_code: str = "en-US",
        prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Generates speech using a Gemini TTS model.

        Args:
            model: TTSModel enum key (e.g. "GEMINI_TTS_FLASH").
            text: The text to synthesize (≤4,000 bytes).
            voice_name: Bare voice name, e.g. "Kore", "Puck".
            language_code: BCP-47 language tag, e.g. "en-US".
            prompt: Optional style/delivery prompt (≤4,000 bytes).
                    Supports markup tags like [sigh], [whispering], etc.
        """
        tts = self._tts
        model_id = TTSModel[model].value

        if prompt:
            synthesis_input = tts.SynthesisInput(text=text, prompt=prompt)
        else:
            synthesis_input = tts.SynthesisInput(text=text)

        voice = tts.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
            model_name=model_id,
        )

        audio_config = tts.AudioConfig(
            audio_encoding=tts.AudioEncoding.LINEAR16
        )

        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        return self._bytes_to_comfy_audio(response.audio_content)

    @api_error_retry
    def generate_speech_gemini_enhanced(
        self,
        model: str,
        text: str,
        voice_name: str = "Kore",
        language_code: str = "en-US",
        style_prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Generates styled speech using Gemini TTS.

        The style_prompt field maps to the Cloud TTS `prompt` field and
        supports natural language style instructions as well as markup tags
        such as [whispering], [shouting], [sarcasm], [long pause], etc.
        """
        return self.generate_speech_gemini(
            model=model,
            text=text,
            voice_name=voice_name,
            language_code=language_code,
            prompt=style_prompt,
        )

    # ------------------------------------------------------------------
    # Chirp 3 HD
    # https://cloud.google.com/text-to-speech/docs/chirp3-hd
    # ------------------------------------------------------------------

    @api_error_retry
    def generate_speech_chirp3_hd(
        self,
        text: str,
        voice_name: str = "en-US-Chirp3-HD-Charon",
        language_code: str = "en-US",
        speaking_rate: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Generates speech using a Chirp 3 HD voice.

        Args:
            text: The text to synthesize. Supports [pause short/long] markup.
            voice_name: Full Chirp 3 HD voice name, e.g. "en-US-Chirp3-HD-Charon".
            language_code: BCP-47 language tag matching the voice locale.
            speaking_rate: Playback speed multiplier (0.25–2.0). Default 1.0.
        """
        tts = self._tts

        synthesis_input = tts.SynthesisInput(text=text)

        voice = tts.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

        audio_config = tts.AudioConfig(
            audio_encoding=tts.AudioEncoding.LINEAR16,
            speaking_rate=speaking_rate
        )

        response = tts.TextToSpeechClient().synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        return self._bytes_to_comfy_audio(response.audio_content)

    # ------------------------------------------------------------------
    # Audio conversion helpers
    # ------------------------------------------------------------------

    def _bytes_to_comfy_audio(self, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Converts WAV audio bytes (LINEAR16 from Cloud TTS) to ComfyUI audio format.

        Cloud TTS LINEAR16 responses include a WAV header, so wave.open works directly.
        """
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

                # Shape: [batch=1, channels, samples]
                waveform_tensor = (
                    torch.from_numpy(waveform_np.copy())
                    .reshape(-1, n_channels)
                    .transpose(0, 1)
                )
                return {"waveform": waveform_tensor.unsqueeze(0), "sample_rate": sample_rate}

        except wave.Error as e:
            raise APIExecutionError(f"Failed to decode audio response: {e}") from e
