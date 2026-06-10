# Copyright 2026 Google LLC
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

from typing import Optional, Tuple

from .constants import (
    AUDIO_MIME_TYPES,
    IMAGE_MIME_TYPES,
    VIDEO_MIME_TYPES,
    Gemini35Model,
    ThresholdOptions,
)
from .custom_exceptions import ConfigurationError
from .gemini_35_api import Gemini35API
from .logger import get_node_logger

logger = get_node_logger(__name__)


class GeminiNode35:
    """
    A ComfyUI node for generating content using Gemini 3.5 models.
    """

    def __init__(self) -> None:
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "prompt": (
                    "STRING",
                    {"multiline": True, "default": "Describe the content in detail."},
                ),
                "model": (
                    [model.name for model in Gemini35Model],
                    {"default": Gemini35Model.GEMINI_35_FLASH.name},
                ),
                # GenerationConfig Parameters
                "temperature": (
                    "FLOAT",
                    {"default": 0.7, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "max_output_tokens": ("INT", {"default": 8192, "min": 1, "max": 8192}),
                "top_p": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "top_k": ("INT", {"default": 32, "min": 1, "max": 64}),
                "candidate_count": ("INT", {"default": 1, "min": 1, "max": 8}),
                "stop_sequences": (
                    "STRING",
                    {
                        "multiline": False,
                        "default": "",
                        "placeholder": "Comma-separated phrases to stop generation",
                    },
                ),
                "response_mime_type": (
                    "STRING",
                    {
                        "default": "text/plain",
                        "combo": ["text/plain", "application/json"],
                    },
                ),
                # Safety Settings
                "harassment_threshold": (
                    [threshold_option.name for threshold_option in ThresholdOptions],
                    {"default": ThresholdOptions.BLOCK_MEDIUM_AND_ABOVE.name},
                ),
                "hate_speech_threshold": (
                    [threshold_option.name for threshold_option in ThresholdOptions],
                    {"default": ThresholdOptions.BLOCK_MEDIUM_AND_ABOVE.name},
                ),
                "sexually_explicit_threshold": (
                    [threshold_option.name for threshold_option in ThresholdOptions],
                    {"default": ThresholdOptions.BLOCK_MEDIUM_AND_ABOVE.name},
                ),
                "dangerous_content_threshold": (
                    [threshold_option.name for threshold_option in ThresholdOptions],
                    {"default": ThresholdOptions.BLOCK_MEDIUM_AND_ABOVE.name},
                ),
            },
            "optional": {
                "system_instruction": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": "",
                        "placeholder": "Optional system instruction for the model",
                    },
                ),
                "image_file_path": (
                    "STRING",
                    {
                        "optional": True,
                        "placeholder": "/path/to/your/image.png",
                        "tooltip": "the absolute path of the image e.g output/file.png",
                    },
                ),
                "image_mime_type": (
                    [image_type for image_type in IMAGE_MIME_TYPES],
                    {"optional": True, "default": "image/png"},
                ),
                "video_file_path": (
                    "STRING",
                    {
                        "optional": True,
                        "placeholder": "/path/to/your/video.mp4",
                        "tooltip": "the absolute path of the video e.g output/file.mp4",
                    },
                ),
                "video_mime_type": (
                    [video_type for video_type in VIDEO_MIME_TYPES],
                    {"optional": True, "default": "video/mp4"},
                ),
                "audio_file_path": (
                    "STRING",
                    {
                        "optional": True,
                        "placeholder": "/path/to/your/audio.mp3",
                        "tooltip": "the absolute path of the audio e.g output/file.mp3",
                    },
                ),
                "audio_mime_type": (
                    [audio_type for audio_type in AUDIO_MIME_TYPES],
                    {"optional": True, "default": "audio/mp3"},
                ),
                "gcp_project_id": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "GCP project id where Vertex AI API will query Gemini",
                    },
                ),
                "gcp_region": (
                    "STRING",
                    {
                        "default": "global",
                        "tooltip": "GCP region for Vertex AI API",
                    },
                ),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("generated_output",)
    FUNCTION = "generate_content"
    CATEGORY = "Google AI/Gemini"

    def generate_content(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_output_tokens: int,
        top_p: float,
        top_k: int,
        candidate_count: int,
        stop_sequences: str,
        response_mime_type: str,
        harassment_threshold: str,
        hate_speech_threshold: str,
        sexually_explicit_threshold: str,
        dangerous_content_threshold: str,
        system_instruction: str = "",
        image_file_path: str = "",
        image_mime_type: str = "image/png",
        video_file_path: str = "",
        video_mime_type: str = "video/mp4",
        audio_file_path: str = "",
        audio_mime_type: str = "audio/mp3",
        gcp_project_id: str = "",
        gcp_region: str = "",
    ) -> Tuple[str,]:
        try:
            gemini_35_api = Gemini35API(
                project_id=gcp_project_id, region=gcp_region
            )
        except ConfigurationError as e:
            raise RuntimeError(f"Gemini 3.5 API Configuration Error: {e}") from e

        try:
            generated_text = gemini_35_api.generate_content(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                top_p=top_p,
                top_k=top_k,
                candidate_count=candidate_count,
                stop_sequences=stop_sequences,
                response_mime_type=response_mime_type,
                harassment_threshold=harassment_threshold,
                hate_speech_threshold=hate_speech_threshold,
                sexually_explicit_threshold=sexually_explicit_threshold,
                dangerous_content_threshold=dangerous_content_threshold,
                system_instruction=system_instruction,
                image_file_path=image_file_path,
                image_mime_type=image_mime_type,
                video_file_path=video_file_path,
                video_mime_type=video_mime_type,
                audio_file_path=audio_file_path,
                audio_mime_type=audio_mime_type,
            )
            return (generated_text,)
        except Exception as e:
            raise RuntimeError(f"Gemini 3.5 API Error: {e}") from e


NODE_CLASS_MAPPINGS = {
    "GeminiNode35": GeminiNode35,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GeminiNode35": "Gemini 3.5",
}
