import json
import logging
import os
from typing import Dict, Any

import yaml

logger = logging.getLogger(__name__)


def _search_paths(file_name: str) -> list[str]:
    """Generate common search paths for a configuration file."""
    return [
        file_name,
        f"../{file_name}",
        os.path.join(os.path.dirname(__file__), "..", file_name),
    ]


def load_llm_config(file_name: str = "llmconfig.yml") -> Dict[str, Any]:
    """Load LLM configuration from YAML file."""
    for path in _search_paths(file_name):
        try:
            if os.path.exists(path):
                logger.info("Found LLM config at: %s", os.path.abspath(path))
                with open(path, "r") as f:
                    config = yaml.safe_load(f)
                    if isinstance(config, dict):
                        logger.info(
                            "Loaded %d models from config", len(config.get("models", {}))
                        )
                        return config
                    logger.error(
                        "Invalid YAML format in %s: expected dict, got %s",
                        path,
                        type(config),
                    )
                    return {}
        except yaml.YAMLError as e:
            logger.error("YAML parsing error in %s: %s", path, e)
            return {}
        except Exception as e:  # pragma: no cover - unexpected errors
            logger.error("Error reading %s: %s", path, e)
            continue

    logger.warning(
        "llmconfig.yml not found in any of these locations: %s", _search_paths(file_name)
    )
    logger.info("Create llmconfig.yml with your LLM configurations to enable model support")
    return {}


def load_mcp_config(file_name: str = "mcp.json") -> Dict[str, Any]:
    """Load MCP server configuration from JSON file."""
    for path in _search_paths(file_name):
        try:
            if os.path.exists(path):
                logger.info("Found MCP config at: %s", os.path.abspath(path))
                with open(path, "r") as f:
                    config = json.load(f)
                    if isinstance(config, dict):
                        logger.info(
                            "Loaded MCP config with %d servers: %s",
                            len(config),
                            list(config.keys()),
                        )
                        return config
                    logger.error(
                        "Invalid JSON format in %s: expected dict, got %s",
                        path,
                        type(config),
                    )
                    return {}
        except json.JSONDecodeError as e:
            logger.error("JSON parsing error in %s: %s", path, e)
            return {}
        except Exception as e:  # pragma: no cover - unexpected errors
            logger.error("Error reading %s: %s", path, e)
            continue

    logger.warning(
        "MCP config file not found in any of these locations: %s", _search_paths(file_name)
    )
    logger.info("Create mcp.json with your MCP server configurations to enable tool support")
    return {}
