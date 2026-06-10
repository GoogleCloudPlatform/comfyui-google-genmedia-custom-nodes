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

from typing import Optional, List

from google import genai
from google.genai import types

from . import utils
from .base import VertexAIClient
from .constants import (
    GEMINI_USER_AGENT,
    Gemini35Model,
    ThresholdOptions,
)
from .custom_exceptions import APIExecutionError, APIInputError, ConfigurationError
from .logger import get_node_logger
from .retry import api_error_retry

logger = get_node_logger(__name__)


class Gemini35API(VertexAIClient):
    """
    A class to interact with the Gemini 3.5 models.
    """

    def __init__(
        self, project_id: Optional[str] = None, region: Optional[str] = None
    ):
        """Initializes the Gemini 3.5 client.
        Args:
            project_id: The GCP project ID. If provided, overrides metadata lookup.
            region: The GCP region. If provided, overrides metadata lookup.

        Raises:
            ConfigurationError: If client initialization fails.
        """
        super().__init__(
            gcp_project_id=project_id,
            gcp_region=region,
            user_agent=GEMINI_USER_AGENT,
        )
        logger.info(
            f"genai.Client initialized for Vertex AI project: {self.project_id}, location: {self.region}"
        )

    @api_error_retry
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
    ) -> str:
        """Generates content using the Gemini 3.5 API based on the provided prompt and parameters.

        Args:
            prompt (str): The main text prompt for the model.
            model (str): The name of the Gemini model to use (e.g., "GEMINI_35_FLASH").
            temperature (float): Controls the randomness of the output.
            max_output_tokens (int): The maximum number of tokens to generate.
            top_p (float): The cumulative probability of tokens to consider.
            top_k (int): The number of highest probability tokens to consider.
            candidate_count (int): The number of alternative responses to generate.
            stop_sequences (str): Comma-separated phrases to stop generation.
            response_mime_type (str): The desired MIME type of the response.
            harassment_threshold (str): Safety threshold for harassment.
            hate_speech_threshold (str): Safety threshold for hate speech.
            sexually_explicit_threshold (str): Safety threshold for sexually explicit.
            dangerous_content_threshold (str): Safety threshold for dangerous content.
            system_instruction (str, optional): Optional system instruction.
            image_file_path (str, optional): Path to an image file.
            image_mime_type (str, optional): MIME type of the image file.
            video_file_path (str, optional): Path to a video file.
            video_mime_type (str, optional): MIME type of the video file.
            audio_file_path (str, optional): Path to an audio file.
            audio_mime_type (str, optional): MIME type of the audio file.

        Returns:
            str: The generated text, or an error/block message.
        """
        # Prepare the request payload
        try:
            # Prepare GenerationConfig
            gen_config_obj = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                top_p=top_p,
                top_k=top_k,
                candidate_count=candidate_count,
            )
            if stop_sequences:
                gen_config_obj.stop_sequences = [
                    s.strip() for s in stop_sequences.split(",") if s.strip()
                ]

            if response_mime_type != "text/plain":
                gen_config_obj.response_mime_type = response_mime_type

            # Prepare Safety Settings
            safety_settings = []
            safety_settings.append(
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=ThresholdOptions[harassment_threshold].value,
                )
            )
            safety_settings.append(
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=ThresholdOptions[hate_speech_threshold].value,
                )
            )
            safety_settings.append(
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=ThresholdOptions[sexually_explicit_threshold].value,
                )
            )
            safety_settings.append(
                types.SafetySetting(
                    category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=ThresholdOptions[dangerous_content_threshold].value,
                )
            )

            gen_config_obj.safety_settings = safety_settings
            # Prepare contents (prompt, text, image, video, audio)
            contents = [types.Part.from_text(text=prompt)]
            image_content = (
                utils.prep_for_media_conversion(image_file_path, image_mime_type)
                if image_file_path
                else logger.info("No image provided")
            )
            if image_content:
                contents.append(image_content)
            else:
                logger.info(
                    f"Image path '{image_file_path}' provided but content not retrieved or file not found."
                )

            video_content = (
                utils.prep_for_media_conversion(video_file_path, video_mime_type)
                if video_file_path
                else logger.info("No video provided")
            )
            if video_content:
                contents.append(video_content)
            else:
                logger.info(
                    f"Video path '{video_file_path}' provided but content not retrieved or file not found."
                )

            audio_content = (
                utils.prep_for_media_conversion(audio_file_path, audio_mime_type)
                if audio_file_path
                else logger.info("No audio provided")
            )
            if audio_content:
                contents.append(audio_content)
            else:
                logger.info(
                    f"Audio path '{audio_file_path}' provided but content not retrieved or file not found."
                )
            # Prepare system instruction
            system_instruction_parts = []
            if system_instruction:
                system_instruction_parts.append(
                    types.Part.from_text(text=system_instruction)
                )

            gen_config_obj.system_instruction = (
                system_instruction_parts if system_instruction_parts else None
            )

        except (KeyError, FileNotFoundError) as e:
            raise APIInputError(f"Invalid input provided: {e}") from e
        except Exception as e:
            raise APIExecutionError(
                f"An unexpected error occurred during request preparation: {e}"
            ) from e

        # Make the API call
        try:
             # Map string model name to Enum
            model_enum = Gemini35Model[model]
            logger.info(
                f"Making Gemini API call with the following Model : {model_enum} , config {gen_config_obj}"
            )
            response = self.client.models.generate_content(
                config=gen_config_obj,
                contents=contents,
                model=model_enum.value,
            )
        except Exception as e:
             raise APIExecutionError(f"Gemini API Call failed: {e}") from e

        # Process the response
        try:
            # Extract and return the generated text
            generated_text = ""
            if response.candidates:
                generated_text = response.candidates[0].content.parts[0].text

            else:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    generated_text = f"Content blocked by safety filter: {response.prompt_feedback.block_reason}"
                    if response.prompt_feedback.safety_ratings:
                        for rating in response.prompt_feedback.safety_ratings:
                            generated_text += f"\n  - Category: {rating.category.name}, Probability: {rating.probability.name}"
                else:
                    generated_text = "No content generated."

            return generated_text
        except (AttributeError, IndexError) as e:
            raise APIExecutionError(
                f"Failed to parse API response, unexpected structure: {e}"
            ) from e
        except Exception as e:
            raise APIExecutionError(
                f"An unexpected error occurred during response processing: {e}"
            ) from e
