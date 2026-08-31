import secrets

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def require_internal_api_key(x_internal_api_key: str = Header(...)) -> None:
    expected = get_settings().internal_api_key
    if not secrets.compare_digest(x_internal_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )

