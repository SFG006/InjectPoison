import os
from fastapi import HTTPException , Security , status
from fastapi.security import APIKeyHeader
from fsspec.implementations.cache_metadata import Detail

# Look for 'X-API-Key' in the HTTP request headers
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# For local development, we define a default key.
# In production, this can be pulled from a database or Redis cache.
VALID_API_KEYS = {
    os.getenv("DEV_API_KEY", "injectpoison_secret_test_key_123")
}

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """
    Validates whether the incoming request contains an authorized API key.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Pass 'X-API-Key' header."
        )

    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            dtail="Invalid or expired API Key."
        )
    return api_key

    