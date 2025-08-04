import os
from fastapi import HTTPException, Header
from typing import Optional
from config import config


async def verify_token(x_token: Optional[str] = Header(None)) -> str:
    """
    Verify the x-token header for API authentication.

    Args:
        x_token: The token from the x-token header

    Returns:
        The verified token

    Raises:
        HTTPException: If token is missing or invalid
    """
    if not x_token:
        raise HTTPException(
            status_code=401,
            detail="Missing x-token header. Please include 'x-token' header with your request."
        )

    try:
        expected_token = config.get_token()
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: API token not properly configured."
        )

    if x_token != expected_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid token. Please check your x-token value."
        )

    return x_token


def get_token_from_env() -> str:
    """
    Get the expected token from environment variables.

    Returns:
        The token value from environment

    Raises:
        ValueError: If token is not configured
    """
    return config.get_token()
