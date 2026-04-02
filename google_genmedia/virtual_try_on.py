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

# This is a preview version of Virtual-try-on custom nodes

import base64
from typing import Any, Dict, Optional, Tuple

import torch
from google.genai import types

# RecontextImageSource and ProductImage were added in google-genai >= 1.14.0.
# Accessing via the types module avoids a static-analysis unresolved-import warning
# while still raising a clear error at load time on older SDK versions.
try:
    RecontextImageSource = types.RecontextImageSource
    ProductImage = types.ProductImage
except AttributeError as _vto_import_err:
    raise ImportError(
        "Virtual Try-On requires google-genai >= 1.14.0. "
        "Please run: pip install --upgrade google-genai"
    ) from _vto_import_err

from . import utils
from .base import VertexAIClient
from .constants import VTO_MODEL, VTO_USER_AGENT
from .custom_exceptions import APIExecutionError, APIInputError, ConfigurationError
from .logger import get_node_logger
from .retry import api_error_retry

logger = get_node_logger(__name__)


class VirtualTryOn(VertexAIClient):
    """
    A ComfyUI node for virtual try on.
    """

    def __init__(
        self,
        gcp_project_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initializes the VirtualTryOn client.

        Args:
            gcp_project_id: The GCP project ID. If provided, overrides metadata lookup.
            api_key: The Google GenAI API Key. If provided, prioritizes over environment variable.

        Raises:
            ConfigurationError: If configuration fails or client initialization fails.
        """
        # VTO requires location="global" for Vertex AI
        super().__init__(
            gcp_project_id=gcp_project_id,
            gcp_region="global",
            user_agent=VTO_USER_AGENT,
            api_key=api_key,
        )
        logger.info(
            f"VirtualTryOn client initialized (project: {getattr(self, 'project_id', 'api-key-auth')})"
        )

    @classmethod
    def INPUT_TYPES(cls) -> Dict[str, Dict[str, Any]]:
        """
        Defines the input types and widgets for the ComfyUI node.

        Returns:
            A dictionary specifying the required and optional input parameters.
        """
        return {
            "required": {
                "person_image": ("IMAGE",),
                "product_image": ("IMAGE",),
                "number_of_images": ("INT", {"default": 1, "min": 1, "max": 4}),
            },
            "optional": {
                "api_key": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Google GenAI API Key (prioritized over environment variable)",
                    },
                ),
                "gcp_project_id": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "GCP project id where Vertex AI API will be queried",
                    },
                ),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("Generated Image",)

    FUNCTION = "generate_and_return_image"
    CATEGORY = "Google AI/Virtual-Try-On"

    @api_error_retry
    def _recontext(
        self,
        person_image_bytes: bytes,
        product_image_bytes: bytes,
        number_of_images: int,
        model: str,
    ) -> Any:
        """
        Calls the Virtual Try-On API using the genai client.

        Args:
            person_image_bytes: Raw PNG bytes of the person image.
            product_image_bytes: Raw PNG bytes of the product image.
            number_of_images: Number of images to generate (1–4).
            model: The model ID to use.

        Returns:
            The recontext_image response from the API.

        Raises:
            APIInputError: If input parameters are invalid.
            APIExecutionError: If the API call fails.
        """
        return self.client.models.recontext_image(
            model=model,
            source=RecontextImageSource(
                person_image=types.Image(
                    image_bytes=person_image_bytes, mime_type="image/png"
                ),
                product_images=[
                    ProductImage(
                        product_image=types.Image(
                            image_bytes=product_image_bytes, mime_type="image/png"
                        )
                    )
                ],
            ),
            config={"sample_count": number_of_images},
        )

    def generate_and_return_image(
        self,
        person_image: torch.Tensor,
        product_image: torch.Tensor,
        number_of_images: int,
        api_key: str = "",
        gcp_project_id: Optional[str] = None,
    ) -> Tuple[torch.Tensor,]:
        """
        Generates virtual try-on images via the Google GenAI API.

        Iterates through each provided product image, calls the VTO API with the
        person image, and returns all generated images as a concatenated tensor.

        Args:
            person_image: A PyTorch tensor representing the image of the person.
            product_image: A PyTorch tensor representing the product image(s).
            number_of_images: Number of output images to generate (1–4).
            api_key: Google GenAI API Key.
            gcp_project_id: Optional GCP project ID override.

        Returns:
            A tuple containing a concatenated PyTorch tensor of all generated images.

        Raises:
            RuntimeError: If configuration fails or image generation encounters an error.
        """
        try:
            self.__init__(
                gcp_project_id=gcp_project_id if gcp_project_id else None,
                api_key=api_key if api_key else None,
            )
        except ConfigurationError as e:
            raise RuntimeError(f"Virtual Try-On API Configuration Error: {e}") from e

        try:
            if not (person_image.numel() > 0 and product_image.numel() > 0):
                raise APIInputError(
                    "Both person_image and product_image must be valid, non-empty images."
                )

            person_b64 = utils.tensor_to_pil_to_base64(person_image)
            person_bytes = base64.b64decode(person_b64)

            all_generated_tensors = []

            logger.info(
                f"Beginning batch job for {product_image.shape[0]} product image(s)."
            )
            for i in range(product_image.shape[0]):
                single_product_tensor = product_image[i : i + 1]
                logger.info(f"Processing image {i+1} of {product_image.shape[0]}...")
                product_b64 = utils.tensor_to_pil_to_base64(single_product_tensor)
                product_bytes = base64.b64decode(product_b64)

                try:
                    response = self._recontext(
                        person_image_bytes=person_bytes,
                        product_image_bytes=product_bytes,
                        number_of_images=number_of_images,
                        model=VTO_MODEL,
                    )
                    for generated_image in response.generated_images:
                        img_b64 = base64.b64encode(
                            generated_image.image.image_bytes
                        ).decode("utf-8")
                        tensor = utils.base64_to_pil_to_tensor(img_b64)
                        all_generated_tensors.append(tensor)
                except (APIExecutionError, APIInputError) as e:
                    error_message = (
                        f"Could not generate image for product {i+1}. Error: {e}"
                    )
                    logger.error(error_message)

                    if i == product_image.shape[0] - 1 and not all_generated_tensors:
                        raise APIExecutionError(
                            f"Image generation failed for final product in batch: {e}"
                        ) from e

                    continue

            if not all_generated_tensors:
                raise APIExecutionError(
                    "Image generation failed for all product images in the batch."
                )

        except APIInputError as e:
            raise RuntimeError(f"Virtual Try-On API Input Error: {e}") from e
        except APIExecutionError as e:
            raise RuntimeError(f"Virtual Try-On API Execution Error: {e}") from e
        except Exception as e:
            raise RuntimeError(
                f"An unexpected error occurred during image generation: {e}"
            ) from e

        final_batch_tensor = torch.cat(all_generated_tensors, 0)
        logger.info(
            f"Successfully generated {final_batch_tensor.shape[0]} image(s) in total."
        )
        return (final_batch_tensor,)


NODE_CLASS_MAPPINGS = {"VirtualTryOn": VirtualTryOn}

NODE_DISPLAY_NAME_MAPPINGS = {"VirtualTryOn": "Virtual try-on"}
