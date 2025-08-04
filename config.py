import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration class"""

    # Authentication - must be set via environment variable
    API_TOKEN: str = os.getenv("API_TOKEN")

    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Browser settings
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "120000"))

    # API settings
    MAX_PAGE_COUNT: int = int(os.getenv("MAX_PAGE_COUNT", "20"))

    @classmethod
    def validate_token(cls) -> bool:
        """Validate that a proper token is set"""
        return cls.API_TOKEN is not None and cls.API_TOKEN.strip() != ""

    @classmethod
    def get_token(cls) -> str:
        """Get the API token, raising an error if not configured"""
        if not cls.validate_token():
            raise ValueError(
                "API_TOKEN environment variable is not set. "
                "Please set it in your .env file or environment variables."
            )
        return cls.API_TOKEN


# Global config instance
config = Config()
