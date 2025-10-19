"""
OpenProject MCP Server Configuration
"""
import os
from typing import Optional
from pydantic import BaseSettings, validator


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