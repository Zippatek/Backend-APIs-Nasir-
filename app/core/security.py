"""
Security and JWT utilities
"""
import logging
from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Security scheme
security = HTTPBearer()


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token to verify
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Dependency to get current authenticated user
    
    Args:
        credentials: HTTP Bearer token from request
    
    Returns:
        Decoded token payload with user info
    
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    return verify_token(token)


async def get_current_user_id(current_user: dict = Depends(get_current_user)) -> str:
    """Get current user ID from token"""
    return current_user.get("sub")


async def verify_kyc_status(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Verify user has verified KYC status
    
    Args:
        current_user: Current user from token
    
    Returns:
        User data if KYC is verified
    
    Raises:
        HTTPException: If KYC is not verified
    """
    kyc_status = current_user.get("kyc_status")
    if kyc_status != "verified":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KYC verification required to create listings"
        )
    return current_user


def require_role(*allowed_roles):
    """
    Dependency to require specific user role
    
    Args:
        allowed_roles: Tuple of allowed roles
    
    Returns:
        Dependency function
    """
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {allowed_roles}"
            )
        return current_user
    
    return role_checker
