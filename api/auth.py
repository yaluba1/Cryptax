import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.config import settings
from loguru import logger

# Security scheme for the Authorization header
security = HTTPBearer()

# JWK Client to manage public keys from Hanko
jwks_client = jwt.PyJWKClient(settings.jwks_url)

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Validate the JWT from Hanko and return the user ID (sub).
    
    Args:
        token: The bearer token from the Authorization header.
        
    Returns:
        The subject (user ID) from the token.
        
    Raises:
        HTTPException: If the token is invalid, expired, or missing required claims.
    """
    try:
        # Get the signing key from the JWKS endpoint
        signing_key = jwks_client.get_signing_key_from_jwt(token.credentials)
        
        # Decode and validate the token
        payload = jwt.decode(
            token.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.jwt_audience,
            issuer=settings.hanko_api_url,   # Iss should match Hanko API URL
        )
        
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("Token payload missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user information",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user_id

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
