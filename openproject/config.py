"""
OpenProject MCP Server Configuration
"""
import logging
from pydantic import validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class OpenProjectSettings(BaseSettings):
    """OpenProject configuration with default values"""

    base_url: str = "http://14.103.141.123:8080"
    api_key: str = "539750190b72e7fa4bbdea73ae4a5e467ddeb2dda3963b40ed96a06a6814c273"
    timeout: int = 30

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