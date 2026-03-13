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

import os
import requests

from .logger import get_node_logger

logger = get_node_logger(__name__)


def load_dotenv():
    # Load .env file from the root folder of the custom node
    # Assuming this file is in google_genmedia/config.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    dotenv_path = os.path.join(root_dir, ".env")

    if os.path.exists(dotenv_path):
        logger.info(f"Loading environment variables from {dotenv_path}")
        with open(dotenv_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
    else:
        logger.info(f"No .env file found at {dotenv_path}")


# Run load_dotenv automatically on module import
load_dotenv()


# Fetch GCP project ID and zone required to authenticate with Vertex AI APIs
def get_gcp_metadata(path):
    headers = {"Metadata-Flavor": "Google"}
    try:
        response = requests.get(
            f"http://metadata.google.internal/computeMetadata/v1/{path}",
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.text.strip()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching metadata from {path}: {e}")
        return None
