import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supabase_id = Column(String(255), unique=True, nullable=False, index=True)  # Supabase user ID
    email = Column(String(255), nullable=True, index=True)
    nickname = Column(String(50), nullable=False, index=True)
    color = Column(String(7), nullable=False, default="#3B82F6")  # Hex color
    icon = Column(String(50), nullable=False, default="user")
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agents = relationship("Agent", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.nickname}>"
