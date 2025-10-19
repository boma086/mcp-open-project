"""
OpenProject MCP Server - Main Server Implementation
"""
import asyncio
import os
import yaml
from pathlib import Path
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from openproject.config import OpenProjectSettings


async def create_mcp_server():
    """Create MCP server using local spec.yml"""

    # Load configuration
    config = OpenProjectSettings()
    client = config.get_client()

    # Load OpenAPI spec from local file
    spec_path = Path(__file__).parent.parent / "spec.yml"
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            openapi_spec = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"OpenAPI spec file not found: {spec_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in OpenAPI spec: {e}")

    # Create MCP server (simplified version - no route maps initially)
    mcp = FastMCP(
        name="OpenProject MCP Server",
        description="MCP server for OpenProject project management"
    )

    # Load OpenAPI spec into MCP server
    # Note: FastMCP.from_openapi() is the recommended method
    mcp_server = FastMCP.from_openapi(
        openapi_spec=openapi_spec,
        client=client,
        name="OpenProject MCP Server"
    )

    return mcp_server


def main():
    """Main entry point with HTTP server setup"""
    print("OpenProject MCP Server starting...")

    # Create MCP server
    mcp = asyncio.run(create_mcp_server())

    # Setup Starlette app with CORS for cross-origin requests
    app = mcp.streamable_http_app()

    # IMPORTANT: add CORS middleware for browser based clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id", "mcp-protocol-version"],
        max_age=86400,
    )

    # Get port from environment variable (Smithery sets this to 8081)
    port = int(os.environ.get("PORT", 8080))
    print(f"Listening on port {port}")

    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="debug")


if __name__ == "__main__":
    main()