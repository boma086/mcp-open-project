"""
OpenProject MCP Server - Main Server Implementation
"""
import asyncio
import os
import yaml
import logging
from pathlib import Path
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from fastmcp import FastMCP
from openproject.config import OpenProjectSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_openapi_spec():
    """Load OpenAPI spec with error handling"""
    spec_path = Path(__file__).parent.parent / "spec.yml"
    logger.info(f"Loading OpenAPI spec from: {spec_path}")

    try:
        if not spec_path.exists():
            logger.error(f"OpenAPI spec file not found: {spec_path}")
            raise FileNotFoundError(f"OpenAPI spec file not found: {spec_path}")

        with open(spec_path, 'r', encoding='utf-8') as f:
            openapi_spec = yaml.safe_load(f)

        paths_count = len(openapi_spec.get('paths', {}))
        logger.info(f"Successfully loaded OpenAPI spec with {paths_count} paths")
        return openapi_spec

    except yaml.YAMLError as e:
        logger.error(f"Invalid YAML in OpenAPI spec: {e}")
        raise ValueError(f"Invalid YAML in OpenAPI spec: {e}")
    except Exception as e:
        logger.error(f"Error loading OpenAPI spec: {e}")
        raise


async def create_mcp_server():
    """Create MCP server with proper error handling"""
    logger.info("Creating MCP server...")

    try:
        # Load configuration with fallback
        config = OpenProjectSettings.create_with_fallback()
        logger.info(f"Configuration loaded - Base URL: {config.base_url}")

        # Test client creation (but don't connect yet)
        client = config.get_client()
        logger.info("HTTP client created successfully")

        # Load OpenAPI spec
        openapi_spec = load_openapi_spec()

        # Create MCP server using FastMCP.from_openapi
        logger.info("Creating FastMCP server from OpenAPI spec...")
        mcp_server = FastMCP.from_openapi(
            openapi_spec=openapi_spec,
            client=client,
            name="OpenProject MCP Server",
            description="MCP server for OpenProject project management"
        )

        logger.info("MCP server created successfully")
        return mcp_server

    except Exception as e:
        logger.error(f"Failed to create MCP server: {e}")
        raise


def main():
    """Main entry point with improved error handling"""
    logger.info("OpenProject MCP Server starting...")

    # Log environment info
    port = int(os.environ.get("PORT", 8081))
    logger.info(f"Port configured: {port}")
    logger.info(f"Working directory: {os.getcwd()}")

    # Check if spec.yml exists
    spec_path = Path(__file__).parent.parent / "spec.yml"
    logger.info(f"Spec file exists: {spec_path.exists()}")

    try:
        # Create MCP server
        mcp = asyncio.run(create_mcp_server())

        # Get Starlette app from FastMCP
        app = mcp.streamable_http_app()
        logger.info("FastMCP streamable_http_app() created successfully")

        # ⚠️ IMPORTANT: Add custom routes BEFORE CORS middleware
        @app.route("/health")
        async def health_check(request):
            return JSONResponse({
                "status": "healthy",
                "service": "openproject-mcp-server",
                "version": "0.0.1"
            })

        @app.route("/")
        async def root(request):
            return JSONResponse({
                "service": "OpenProject MCP Server",
                "status": "running",
                "mcp_endpoint": "/mcp",
                "version": "0.0.1"
            })

        # Add CORS middleware AFTER custom routes
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id", "mcp-protocol-version"],
            max_age=86400,
        )
        logger.info("CORS middleware configured")

        logger.info(f"Starting HTTP server on port {port}")

        # Log the app routes for debugging
        logger.info("App routes configured:")
        if hasattr(app, 'routes'):
            for route in app.routes:
                logger.info(f"  - {route.methods} {route.path}")

        logger.info(f"Starting HTTP server on port {port}")

        # Run the server with optimized settings for Smithery
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True,
            timeout_keep_alive=65,
            timeout_graceful_shutdown=30
        )

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        # Print the full exception for debugging
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()