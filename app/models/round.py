import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Integer, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class RoundStatus(str, PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"


class Round(Base):
    __tablename__ = "rounds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    status = Column(Enum(RoundStatus), default=RoundStatus.PENDING, nullable=False)
    market_seed = Column(Integer, nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    price_data = Column(JSONB, nullable=True)  # Populated after simulation
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agents = relationship("Agent", back_populates="round", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Round {self.name} ({self.status})>"
