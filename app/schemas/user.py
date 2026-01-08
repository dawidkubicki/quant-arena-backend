from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    nickname: Optional[str] = Field(None, min_length=2, max_length=50)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)


class UserResponse(BaseModel):
    """Schema for user response."""
    id: UUID
    supabase_id: str
    email: Optional[str] = None
    nickname: str
    color: str
    icon: str
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserPublicResponse(BaseModel):
    """Public user info (for leaderboard, etc.)."""
    id: UUID
    nickname: str
    color: str
    icon: str
    
    class Config:
        from_attributes = True
