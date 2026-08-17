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

# This is a preview version of Google GenAI custom nodes

from typing import Optional

from google import genai

from .config import (
    CREDENTIALS_JSON_ENV_VAR,
    LOCATION_ENV_VAR,
    PROJECT_ENV_VAR,
    resolve_vertex_ai_config,
)
from .custom_exceptions import ConfigurationError
from .logger import get_node_logger

logger = get_node_logger(__name__)


class VertexAIClient:
    """
    A base class for initializing Vertex AI clients.
    """

    def __init__(
        self,
        gcp_project_id: Optional[str] = None,
        gcp_region: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        Initializes the Vertex AI client.

        Args:
            gcp_project_id: The GCP project ID. If provided, overrides every
                other source.
            gcp_region: The GCP region. If provided, overrides every other source.
            user_agent: The user agent string for the client.

        Raises:
            ConfigurationError: If GCP Project or region cannot be determined,
                or if configured credentials cannot be used.
        """
        self.credentials, self.project_id, self.region = resolve_vertex_ai_config(
            gcp_project_id, gcp_region
        )

        if not self.project_id:
            raise ConfigurationError(
                "GCP Project is required and could not be determined. Set it on the node, "
                f"or set {CREDENTIALS_JSON_ENV_VAR} to a service account key containing it, "
                f"or set {PROJECT_ENV_VAR}."
            )
        if not self.region:
            raise ConfigurationError(
                "GCP region is required and could not be determined. Set it on the node, "
                f"or set {LOCATION_ENV_VAR}."
            )

        logger.info(f"Project is {self.project_id}, region is {self.region}")

        if user_agent:
            http_options = genai.types.HttpOptions(headers={"user-agent": user_agent})
            client_kwargs = {
                "vertexai": True,
                "project": self.project_id,
                "location": self.region,
                "http_options": http_options,
            }
            # Only passed when the environment supplied credentials; otherwise the
            # client discovers Application Default Credentials exactly as before.
            if self.credentials:
                client_kwargs["credentials"] = self.credentials
            try:
                self.client = genai.Client(**client_kwargs)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to initialize genai.Client for Vertex AI: {e}"
                )
