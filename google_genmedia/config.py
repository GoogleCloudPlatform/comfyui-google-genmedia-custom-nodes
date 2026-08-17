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

import json
import os
import re
from typing import Optional, Tuple

import requests
from google.auth import exceptions as google_auth_exceptions
from google.oauth2 import service_account

from .custom_exceptions import ConfigurationError
from .logger import get_node_logger

logger = get_node_logger(__name__)

# Google publishes no standard environment variable for *inline* service account
# JSON: GOOGLE_APPLICATION_CREDENTIALS is defined as a file path. This is the
# widely used de-facto convention for the inline case, and it deliberately does
# not shadow the standard variable, which other Google libraries in the same
# process still read as a path.
CREDENTIALS_JSON_ENV_VAR = "GOOGLE_APPLICATION_CREDENTIALS_JSON"
PROJECT_ENV_VAR = "GOOGLE_CLOUD_PROJECT"
LOCATION_ENV_VAR = "GOOGLE_CLOUD_LOCATION"

VERTEX_AI_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

_WINDOWS_DRIVE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


def _looks_like_file_path(value: str) -> bool:
    """Reports whether a credential value is an absolute path.

    Only absolute paths are recognised: a leading path separator, or a Windows
    drive letter. A relative path is not a supported form - it would be
    ambiguous against the working directory ComfyUI happens to run from - so it
    is rejected with a dedicated error rather than being treated as JSON.
    """
    return value.startswith(("/", "\\")) or bool(_WINDOWS_DRIVE_PATH.match(value))


def get_credentials_from_env() -> Tuple[Optional[service_account.Credentials], Optional[str]]:
    """Loads service account credentials from the environment, if configured.

    Reads CREDENTIALS_JSON_ENV_VAR, which may hold either the full contents of a
    service account key file or a path to one. This is what allows the nodes to
    authenticate without the gcloud CLI.

    Returns:
        A (credentials, project_id) tuple. Both are None when the variable is
        unset or empty, which leaves the caller on Application Default
        Credentials. The project ID is the one embedded in the key.

    Raises:
        ConfigurationError: If the variable is set but cannot be used. The error
            names the variable and the problem, never the value itself.
    """
    raw_value = os.environ.get(CREDENTIALS_JSON_ENV_VAR, "").strip()
    if not raw_value:
        return None, None

    if _looks_like_file_path(raw_value):
        if not os.path.isfile(raw_value):
            raise ConfigurationError(
                f"{CREDENTIALS_JSON_ENV_VAR} looks like a file path, but no file exists there. "
                "Set it to the path of a service account key file, or to the key's JSON content."
            )
        try:
            credentials = service_account.Credentials.from_service_account_file(
                raw_value, scopes=VERTEX_AI_SCOPES
            )
        except (ValueError, google_auth_exceptions.GoogleAuthError) as e:
            raise ConfigurationError(
                f"{CREDENTIALS_JSON_ENV_VAR} points at a file that is not a usable "
                f"service account key: {e}"
            ) from e
        source = "key file"
    else:
        if not raw_value.startswith("{"):
            raise ConfigurationError(
                f"{CREDENTIALS_JSON_ENV_VAR} is set to something that is neither service "
                "account JSON nor an absolute path to a key file. Set it to the full "
                "contents of a service account key, or to an absolute path such as "
                "/keys/service-account.json or C:\\keys\\service-account.json."
            )
        try:
            key_info = json.loads(raw_value)
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"{CREDENTIALS_JSON_ENV_VAR} is set but its content is not valid JSON "
                f"({e.msg}, line {e.lineno} column {e.colno}). Set it to the full contents "
                "of a service account key file, or to the path of one."
            ) from e
        try:
            credentials = service_account.Credentials.from_service_account_info(
                key_info, scopes=VERTEX_AI_SCOPES
            )
        except (ValueError, google_auth_exceptions.GoogleAuthError) as e:
            raise ConfigurationError(
                f"{CREDENTIALS_JSON_ENV_VAR} contains JSON that is not a usable "
                f"service account key: {e}"
            ) from e
        source = "inline JSON"

    # Never log the credential itself - only where it came from and who it is.
    logger.info(
        f"Loaded service account credentials from {CREDENTIALS_JSON_ENV_VAR} ({source}) "
        f"for service account {getattr(credentials, 'service_account_email', 'unknown')}"
    )
    return credentials, getattr(credentials, "project_id", None)


def _region_from_zone_metadata() -> Optional[str]:
    """Derives a region from the Compute Engine zone metadata, if available."""
    zone_metadata = get_gcp_metadata("instance/zone")
    if not zone_metadata:
        return None
    try:
        zone_name = zone_metadata.split("/")[-1]
        return "-".join(zone_name.split("-")[:-1])
    except Exception as e:
        logger.error(f"Failed to parse region from zone metadata '{zone_metadata}': {e}")
        return None


def resolve_vertex_ai_config(
    gcp_project_id: Optional[str] = None, gcp_region: Optional[str] = None
) -> Tuple[Optional[service_account.Credentials], Optional[str], Optional[str]]:
    """Resolves the credentials, project and region a Vertex AI client needs.

    Precedence, highest first:
        credentials: CREDENTIALS_JSON_ENV_VAR, then Application Default
            Credentials (which itself covers a gcloud login and Compute Engine
            metadata), signalled by returning None.
        project:     the node's field, the project inside the service account
            key, PROJECT_ENV_VAR, then Compute Engine metadata.
        region:      the node's field, LOCATION_ENV_VAR, then the region derived
            from Compute Engine zone metadata.

    Args:
        gcp_project_id: The project from the node's field, if the user set one.
        gcp_region: The region from the node's field, if the user set one.

    Returns:
        A (credentials, project_id, region) tuple. Any element may be None when
        no source supplied it; callers decide which are mandatory.

    Raises:
        ConfigurationError: If credentials are configured but unusable.
    """
    credentials, credentials_project_id = get_credentials_from_env()

    project_id = (
        gcp_project_id
        or credentials_project_id
        or os.environ.get(PROJECT_ENV_VAR)
        # Only reached when nothing above supplied a project: off a Compute
        # Engine VM this call has to time out before it can fail.
        or get_gcp_metadata("project/project-id")
    )

    region = gcp_region or os.environ.get(LOCATION_ENV_VAR) or _region_from_zone_metadata()

    return credentials, project_id, region


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
