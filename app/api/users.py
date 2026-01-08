from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserPublicResponse
from app.utils.auth import get_current_user, get_current_admin

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return current_user


@router.get("/", response_model=list[UserPublicResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only).
    Returns public user info only.
    """
    users = db.query(User).filter(
        User.supabase_id != "ghost"  # Exclude ghost user
    ).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserPublicResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db)
):
    """Get public info for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
