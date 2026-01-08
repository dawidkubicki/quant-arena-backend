import uuid
from typing import Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import get_settings
from app.database import get_db
from app.models.user import User

settings = get_settings()
security = HTTPBearer()


def verify_supabase_token(token: str) -> dict:
    """
    Verify a Supabase JWT token and return the payload.
    
    The token is signed with the Supabase JWT secret.
    """
    try:
        # Supabase uses HS256 algorithm with the JWT secret
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_or_create_user(db: Session, supabase_payload: dict) -> User:
    """
    Get or create a user in our database based on Supabase user data.
    
    Supabase payload contains:
    - sub: Supabase user ID (UUID)
    - email: User's email
    - user_metadata: Custom user metadata (nickname, color, icon, etc.)
    """
    supabase_id = supabase_payload.get("sub")
    email = supabase_payload.get("email", "")
    user_metadata = supabase_payload.get("user_metadata", {})
    
    if not supabase_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID"
        )
    
    # Try to find existing user by Supabase ID
    user = db.query(User).filter(User.supabase_id == supabase_id).first()
    
    if user:
        # Update user info from Supabase metadata if changed
        nickname = user_metadata.get("nickname") or user_metadata.get("name") or email.split("@")[0]
        color = user_metadata.get("color", user.color)
        icon = user_metadata.get("icon", user.icon)
        
        if user.nickname != nickname or user.color != color or user.icon != icon:
            user.nickname = nickname
            user.color = color
            user.icon = icon
            user.email = email
            db.commit()
            db.refresh(user)
    else:
        # Create new user
        nickname = user_metadata.get("nickname") or user_metadata.get("name") or email.split("@")[0]
        color = user_metadata.get("color", "#3B82F6")
        icon = user_metadata.get("icon", "user")
        
        # Check if this email is an admin
        is_admin = email.lower() in [e.lower() for e in settings.admin_emails]
        
        user = User(
            id=uuid.uuid4(),
            supabase_id=supabase_id,
            email=email,
            nickname=nickname,
            color=color,
            icon=icon,
            is_admin=is_admin
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Validate Supabase JWT token and return the current user.
    Creates the user in our database if they don't exist.
    """
    token = credentials.credentials
    payload = verify_supabase_token(token)
    user = get_or_create_user(db, payload)
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Require the current user to be an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optionally authenticate a user. Returns None if no valid token provided.
    """
    if credentials is None:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None
