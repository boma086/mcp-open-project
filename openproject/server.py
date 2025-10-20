"""
OpenProject MCP Server - Main Server Implementation
"""
import asyncio
import os
import yaml
import logging
import time
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
        # Enable experimental OpenAPI parser (required for OpenProject's schema)
        os.environ["FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER"] = "true"
        logger.info("Enabled experimental OpenAPI parser")

        # Load configuration with default values
        config = OpenProjectSettings()
        logger.info(f"Configuration loaded - Base URL: {config.base_url}")

        # Create HTTP client for OpenProject API
        logger.info("Creating HTTP client for OpenProject API...")
        client = config.get_client()
        logger.info("HTTP client created successfully")

        # Load OpenAPI specification
        logger.info("Loading OpenAPI specification...")
        openapi_spec = load_openapi_spec()

        # Create MCP server from OpenAPI spec with route exclusions
        logger.info("Creating FastMCP server from OpenAPI specification...")

        # Try using the new experimental OpenAPI parser
        try:
            from fastmcp.server.openapi_new import FastMCPOpenAPI
            logger.info("Using new experimental OpenAPI parser module")

            mcp_server = FastMCPOpenAPI(
                openapi_spec=openapi_spec,
                client=client,
                name="OpenProject MCP Server"
            )
        except (ImportError, Exception) as e:
            logger.warning(f"OpenAPI parser failed: {e}")
            logger.warning("Falling back to manual OpenProject API tools")

            # Fallback to manual OpenProject tools
            mcp_server = FastMCP(name="OpenProject MCP Server")

            # Add basic status tool
            @mcp_server.tool()
            def get_status() -> str:
                """Get the current status of the OpenProject MCP server"""
                return "OpenProject MCP Server is running with manual API tools (enhanced fallback mode)"

            # Add project management tools for weekly reports
            @mcp_server.tool()
            async def get_projects() -> str:
                """Get all projects from OpenProject"""
                try:
                    response = await client.get("/api/v3/projects")
                    response.raise_for_status()
                    return f"Projects retrieved successfully: {response.json()}"
                except Exception as e:
                    return f"Error retrieving projects: {str(e)}"

            @mcp_server.tool()
            async def get_project_work_packages(project_id: str, status_filter: str = "open") -> str:
                """Get work packages for a specific project with status filtering

                Args:
                    project_id: The ID of the project
                    status_filter: Status filter - 'open' for open work packages, 'all' for all
                """
                try:
                    # Build filters based on status
                    if status_filter == "open":
                        filters = '[{ "status": { "operator": "o", "values": [] } }]'
                    else:
                        filters = '[]'

                    params = {"filters": filters}
                    response = await client.get(f"/api/v3/projects/{project_id}/work_packages", params=params)
                    response.raise_for_status()
                    data = response.json()

                    # Extract key information for reporting
                    total_count = data.get("total", 0)
                    work_packages = data.get("_embedded", {}).get("elements", [])

                    result = {
                        "project_id": project_id,
                        "total_work_packages": total_count,
                        "status_filter": status_filter,
                        "work_packages": [
                            {
                                "id": wp.get("id"),
                                "subject": wp.get("subject"),
                                "status": wp.get("_embedded", {}).get("status", {}).get("name"),
                                "assignee": wp.get("_embedded", {}).get("assignee", {}).get("name"),
                                "dueDate": wp.get("dueDate"),
                                "percentageDone": wp.get("percentageDone")
                            } for wp in work_packages[:10]  # Limit to first 10 for readability
                        ]
                    }

                    return f"Project work packages: {result}"

                except Exception as e:
                    return f"Error retrieving project work packages: {str(e)}"

            @mcp_server.tool()
            async def get_overdue_work_packages(days_ahead: int = 7) -> str:
                """Get work packages that are due within specified days

                Args:
                    days_ahead: Number of days ahead to check for due work packages
                """
                try:
                    # Filter for work packages due in the next N days
                    filters = f'[{{ "dueDate": {{ "operator": "<t+", "values": ["{days_ahead}"] }} }}]'
                    params = {"filters": filters}

                    response = await client.get("/api/v3/work_packages", params=params)
                    response.raise_for_status()
                    data = response.json()

                    total_count = data.get("total", 0)
                    work_packages = data.get("_embedded", {}).get("elements", [])

                    result = {
                        "days_ahead": days_ahead,
                        "total_overdue": total_count,
                        "urgent_work_packages": [
                            {
                                "id": wp.get("id"),
                                "subject": wp.get("subject"),
                                "project": wp.get("_embedded", {}).get("project", {}).get("name"),
                                "status": wp.get("_embedded", {}).get("status", {}).get("name"),
                                "assignee": wp.get("_embedded", {}).get("assignee", {}).get("name"),
                                "dueDate": wp.get("dueDate"),
                                "percentageDone": wp.get("percentageDone")
                            } for wp in work_packages[:15]  # Limit to first 15 most urgent
                        ]
                    }

                    return f"Overdue/Urgent work packages: {result}"

                except Exception as e:
                    return f"Error retrieving overdue work packages: {str(e)}"

            @mcp_server.tool()
            async def get_user_info(user_id: str) -> str:
                """Get detailed information about a specific user

                Args:
                    user_id: The ID of the user
                """
                try:
                    response = await client.get(f"/api/v3/users/{user_id}")
                    response.raise_for_status()
                    return f"User information: {response.json()}"
                except Exception as e:
                    return f"Error retrieving user info: {str(e)}"

            @mcp_server.tool()
            async def generate_weekly_report(project_ids: list = None) -> str:
                """Generate a comprehensive weekly report for specified projects or all projects

                Args:
                    project_ids: Optional list of project IDs. If empty, reports on all projects.
                """
                try:
                    report = {
                        "report_type": "weekly_project_summary",
                        "generated_at": "2025-10-20",
                        "projects_summary": []
                    }

                    # Get projects if not specified
                    if not project_ids:
                        projects_response = await client.get("/api/v3/projects")
                        projects_data = projects_response.json()
                        project_ids = [str(p.get("id")) for p in projects_data.get("_embedded", {}).get("elements", [])]

                    # Analyze each project
                    for project_id in project_ids[:5]:  # Limit to 5 projects for performance
                        # Get project info
                        project_response = await client.get(f"/api/v3/projects/{project_id}")
                        project_data = project_response.json()

                        # Get work packages (open and closed)
                        open_wp_response = await client.get(
                            f"/api/v3/projects/{project_id}/work_packages",
                            params={"filters": '[{ "status": { "operator": "o", "values": [] } }]'}
                        )
                        open_wp_data = open_wp_response.json()

                        # Get overdue work packages
                        overdue_response = await client.get(
                            f"/api/v3/projects/{project_id}/work_packages",
                            params={"filters": '[{ "dueDate": { "operator": "<t+", "values": ["7"] } }]'}
                        )
                        overdue_data = overdue_response.json()

                        project_summary = {
                            "project_id": project_id,
                            "project_name": project_data.get("name"),
                            "total_open_work_packages": open_wp_data.get("total", 0),
                            "urgent_work_packages": overdue_data.get("total", 0),
                            "completion_percentage": _calculate_project_completion(open_wp_data)
                        }

                        report["projects_summary"].append(project_summary)

                    return f"Weekly report generated: {report}"

                except Exception as e:
                    return f"Error generating weekly report: {str(e)}"

            # Helper function for project completion calculation
            def _calculate_project_completion(work_packages_data):
                """Calculate approximate project completion based on work packages"""
                try:
                    work_packages = work_packages_data.get("_embedded", {}).get("elements", [])
                    if not work_packages:
                        return 0

                    total_percentage = sum(wp.get("percentageDone", 0) for wp in work_packages)
                    return round(total_percentage / len(work_packages), 1)
                except:
                    return 0

        logger.info("FastMCP server with OpenProject tools created successfully")
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

        # Add request logging middleware
        @app.middleware("http")
        async def log_requests(request, call_next):
            logger.info(f"🔗 Incoming request: {request.method} {request.url}")
            start_time = time.time()

            try:
                response = await call_next(request)
                duration = time.time() - start_time
                logger.info(f"✅ Request completed: {response.status_code} in {duration:.2f}s")
                return response
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"❌ Request failed in {duration:.2f}s: {e}")
                raise

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