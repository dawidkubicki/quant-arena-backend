from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.utils.auth import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's information.
    
    This endpoint validates the Supabase JWT token and returns the user's profile.
    If the user doesn't exist in our database, they are automatically created.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_user_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the current user's profile (nickname, color, icon).
    
    Note: Changes here are stored in our database. To persist across sessions,
    also update the user_metadata in Supabase from the frontend.
    """
    # Check if new nickname is taken by someone else
    if data.nickname and data.nickname.lower() != current_user.nickname.lower():
        existing = db.query(User).filter(
            User.nickname.ilike(data.nickname),
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nickname already taken"
            )
        current_user.nickname = data.nickname
    
    if data.color:
        current_user.color = data.color
    
    if data.icon:
        current_user.icon = data.icon
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/verify")
def verify_token(current_user: User = Depends(get_current_user)):
    """
    Verify that the current token is valid.
    Returns basic user info and admin status.
    """
    return {
        "valid": True,
        "user_id": str(current_user.id),
        "is_admin": current_user.is_admin,
        "nickname": current_user.nickname
    }
