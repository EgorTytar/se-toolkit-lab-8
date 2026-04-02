#!/usr/bin/env python3
"""
Nanobot gateway entrypoint.

Resolves environment variables into config.json at runtime, then launches
`nanobot gateway`. This allows Docker to pass config via env vars.
"""

import json
import os
import sys
from pathlib import Path


def main():
    # Paths
    config_dir = Path("/app/nanobot")
    config_path = config_dir / "config.json"
    resolved_path = config_dir / "config.resolved.json"
    workspace_dir = config_dir / "workspace"

    # Read base config
    if not config_path.exists():
        print(f"Error: Config not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r") as f:
        config = json.load(f)

    # Resolve LLM provider from environment
    llm_api_key = os.environ.get("LLM_API_KEY", "")
    llm_api_base = os.environ.get("LLM_API_BASE_URL", "")
    llm_api_model = os.environ.get("LLM_API_MODEL", "")

    if llm_api_key:
        config["providers"]["custom"]["apiKey"] = llm_api_key
    if llm_api_base:
        config["providers"]["custom"]["apiBase"] = llm_api_base
    if llm_api_model:
        config["agents"]["defaults"]["model"] = llm_api_model

    # Resolve gateway host/port from environment
    gateway_host = os.environ.get("NANOBOT_GATEWAY_CONTAINER_ADDRESS", "")
    gateway_port = os.environ.get("NANOBOT_GATEWAY_CONTAINER_PORT", "")

    if gateway_host:
        config.setdefault("gateway", {})["host"] = gateway_host
    if gateway_port:
        config.setdefault("gateway", {})["port"] = int(gateway_port)

    # Resolve webchat host/port from environment
    webchat_host = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_ADDRESS", "")
    webchat_port = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_PORT", "")

    if webchat_port:
        # Webchat channel config
        if "webchat" not in config.get("channels", {}):
            config.setdefault("channels", {})["webchat"] = {}
        config["channels"]["webchat"]["port"] = int(webchat_port)
        config["channels"]["webchat"]["host"] = webchat_host or "0.0.0.0"

    # Resolve MCP server environment variables
    backend_url = os.environ.get("NANOBOT_LMS_BACKEND_URL", "")
    backend_api_key = os.environ.get("NANOBOT_LMS_API_KEY", "")

    if "mcpServers" in config.get("tools", {}):
        if backend_url:
            config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_BACKEND_URL"] = backend_url
        if backend_api_key:
            config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_API_KEY"] = backend_api_key

    # Write resolved config
    with open(resolved_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Resolved config written to {resolved_path}")

    # Launch nanobot gateway
    os.execvp(
        "nanobot",
        [
            "nanobot",
            "gateway",
            "--config",
            str(resolved_path),
            "--workspace",
            str(workspace_dir),
        ],
    )


if __name__ == "__main__":
    main()
