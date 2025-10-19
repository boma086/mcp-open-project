"""
OpenProject MCP Server Configuration
"""
import os
import logging
from typing import Optional
from pydantic import BaseSettings, validator

logger = logging.getLogger(__name__)


class OpenProjectSettings(BaseSettings):
    """OpenProject configuration with validation"""

    base_url: str
    api_key: str
    timeout: int = 30

    class Config:
        env_prefix = "OPENPROJECT"

    @validator('base_url')
    def validate_base_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('base_url must start with http:// or https://')
        return v.rstrip('/')

    @validator('api_key')
    def validate_api_key(cls, v):
        if len(v) < 10:
            raise ValueError('api_key appears too short')
        return v

    def get_client(self):
        """Create optimized HTTP client"""
        import httpx
        logger.info(f"Creating HTTP client for {self.base_url}")
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/hal+json,application/json"
            },
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=10)
        )

    @classmethod
    def create_with_fallback(cls):
        """Create settings with Smithery environment variable fallback"""
        logger.info("Creating OpenProject settings...")

        # Log all environment variables that start with OPENPROJECT
        env_vars = {k: v for k, v in os.environ.items() if k.startswith('OPENPROJECT') or 'openproject' in k.lower()}
        logger.info(f"Found environment variables: {list(env_vars.keys())}")

        try:
            # Try normal creation first
            return cls()
        except Exception as e:
            logger.warning(f"Failed to create settings with standard env vars: {e}")

            # Try with Smithery camelCase variables as fallback
            smithery_mappings = {
                'base_url': os.getenv('openprojectBaseUrl'),
                'api_key': os.getenv('openprojectApiKey'),
                'timeout': int(os.getenv('openprojectTimeout', '30'))
            }

            logger.info(f"Trying Smithery fallbacks: {smithery_mappings}")

            # Validate required fields
            if not smithery_mappings['base_url']:
                raise ValueError("OPENPROJECT_BASE_URL or openprojectBaseUrl is required")
            if not smithery_mappings['api_key']:
                raise ValueError("OPENPROJECT_API_KEY or openprojectApiKey is required")

            return cls(**smithery_mappings)