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

import configparser
import importlib
import logging
import os
import sys
from .google_genmedia import (
    gemini_flash_image_node,
    gemini_nodes,
    gemini_pro_image_node,
    helper_nodes,
    imagen3_nodes,
    imagen4_nodes,
    lyria2_nodes,
    veo2_nodes,
    veo3_nodes,
    virtual_try_on,
    tts_nodes,
)

# Since ComfyUI uses a root logger with fileConfig(), setting up the custom logger with fileConfig()
# will result in duplicate logging so we are defining the custom logger with ConfigParser() that
# allows us to stop the propagation of the logs to the root logger
def setup_custom_package_logger():
    """
    Reads the custom format, level, handler class, and arguments from logging.conf,
    creates a custom isolated handler, and attaches it to the package logger.
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_dir, "logging.conf")
    config = configparser.ConfigParser(interpolation=None)

    try:
        config.read(config_file)
        if "formatter_customFormatter" not in config:
            logging.warning(
                f"Could not find [formatter_customFormatter] in {config_file}."
            )
            return
        CUSTOM_FORMAT = config["formatter_customFormatter"]["format"]
        custom_formatter = logging.Formatter(CUSTOM_FORMAT)

        if "handler_consoleHandler" not in config:
            logging.warning(
                f"Could not find [handler_consoleHandler] in {config_file}. Skipping."
            )
            return
        # Read and initialize logger with the configs defined in console handler section of the logging.conf
        handler_config = config["handler_consoleHandler"]
        handler_class_str = handler_config["class"]
        handler_args_str = handler_config["args"]
        LOG_LEVEL_STR = handler_config["level"]

        module_name = "logging"
        class_name = handler_class_str
        handler_module = importlib.import_module(module_name)
        HandlerClass = getattr(
            handler_module, class_name
        )  # initializes logging.StreamHandler but will dynamically instantiate any class defined in logging.conf

        # Safely evaluate the arguments (e.g., (sys.stdout,))
        handler_args = eval(handler_args_str, {"sys": sys, "logging": logging})
        custom_handler = HandlerClass(*handler_args)
        LOG_LEVEL = logging.getLevelName(LOG_LEVEL_STR.upper())
        custom_handler.setFormatter(custom_formatter)
        custom_handler.setLevel(LOG_LEVEL)

        package_name = __name__.split(".")[0]
        package_logger = logging.getLogger(package_name)

        # Prevent logs from flowing up to ComfyUI's root logger
        package_logger.propagate = False

        if not package_logger.handlers:
            package_logger.setLevel(LOG_LEVEL)
            package_logger.addHandler(custom_handler)
            package_logger.info(
                f"Initialized isolated custom logger for '{package_name}' using external config."
            )

    except Exception as e:
        logging.error(f"Failed to load or apply logging configuration: {e}")


setup_custom_package_logger()

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

node_modules = [
    gemini_flash_image_node,
    gemini_nodes,
    gemini_pro_image_node,
    helper_nodes,
    imagen3_nodes,
    imagen4_nodes,
    lyria2_nodes,
    lyria3_nodes,
    veo2_nodes,
    veo3_nodes,
    virtual_try_on,
    tts_nodes,
]

for module in node_modules:
    NODE_CLASS_MAPPINGS.update(getattr(module, "NODE_CLASS_MAPPINGS", {}))
    NODE_DISPLAY_NAME_MAPPINGS.update(getattr(module, "NODE_DISPLAY_NAME_MAPPINGS", {}))

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
