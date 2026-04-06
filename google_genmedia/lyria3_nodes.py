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
from typing import Any, Dict, Optional, Tuple

import torch

from . import utils
from .constants import Lyria3Model
from .custom_exceptions import ConfigurationError
from .lyria3_api import Lyria3API


class Lyria3TextToMusicNode:
    """
    A ComfyUI node for generating music from text prompts using the Google Lyria 3 API.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "prompt": (
                    "STRING", 
                    {
                        "multiline": True, 
                        "default": "Genre: Upbeat, acoustic Folk-Pop\nLyrics:\nTail wags and a heavy head,\nTime to curl up in your favorite bed."
                    }
                ),
                "model": ([m.name for m in Lyria3Model], {"default": Lyria3Model.LYRIA_3_PRO.name}),
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
    CATEGORY = "Google AI/Lyria3"

    def generate(
        self,
        prompt: str,
        model: str,
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any],]:
        try:
            init_api_key = api_key if api_key else None
            api = Lyria3API(project_id=gcp_project_id or None, region=gcp_region or None, api_key=init_api_key)
            audio_data = api.generate_music(model=model, prompt=prompt)
            return (audio_data,)
        except Exception as e:
            raise RuntimeError(f"Lyria 3 Text-to-Music generation failed: {e}") from e


class Lyria3ImageToMusicNode:
    """
    A ComfyUI multimodal node for generating music from image and text prompts using the Google Lyria 3 API.
    """

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": ("STRING", {"multiline": True, "default": "Generate an instrumental track based on this input image that starts slowly and builds in intensity."}),
                "model": ([m.name for m in Lyria3Model], {"default": Lyria3Model.LYRIA_3_CLIP.name}),
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
    CATEGORY = "Google AI/Lyria3"

    def generate(
        self,
        image: torch.Tensor,
        prompt: str,
        model: str,
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
    ) -> Tuple[Dict[str, Any],]:
        try:
            if not isinstance(image, torch.Tensor) or image.numel() == 0:
                raise ValueError("Invalid or empty image input tensor")

            # Extract the first image in the batch
            single_image = image[0:1]
            base64_image = utils.tensor_to_pil_to_base64(single_image)
            image_bytes = base64.b64decode(base64_image)

            init_api_key = api_key if api_key else None
            api = Lyria3API(project_id=gcp_project_id or None, region=gcp_region or None, api_key=init_api_key)
            audio_data = api.generate_music_from_image(
                model=model, 
                prompt=prompt, 
                image_bytes=image_bytes, 
                mime_type="image/png"
            )
            return (audio_data,)
        except Exception as e:
            raise RuntimeError(f"Lyria 3 Image-to-Music generation failed: {e}") from e


NODE_CLASS_MAPPINGS = {
    "Lyria3TextToMusicNode": Lyria3TextToMusicNode,
    "Lyria3ImageToMusicNode": Lyria3ImageToMusicNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Lyria3TextToMusicNode": "Lyria 3 Text To Music",
    "Lyria3ImageToMusicNode": "Lyria 3 Image To Music",
}
