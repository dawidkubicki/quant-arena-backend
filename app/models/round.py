import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Integer, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class RoundStatus(str, PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Round(Base):
    """
    A trading simulation round.
    
    Contains market configuration and stores price data and SPY benchmark
    returns after simulation completes.
    """
    __tablename__ = "rounds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    status = Column(Enum(RoundStatus), default=RoundStatus.PENDING, nullable=False)
    market_seed = Column(Integer, nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    
    # Market data (populated after simulation)
    # Each stores list of {tick, timestamp, value} objects for charting
    price_data = Column(JSONB, nullable=True)  # AAPL close prices with timestamps
    spy_returns = Column(JSONB, nullable=True)  # SPY log returns with timestamps
    timestamps = Column(JSONB, nullable=True)  # ISO timestamps for each tick (None for synthetic data)
    
    # Progress tracking for async simulation
    progress = Column(Integer, default=0, nullable=False)  # 0-100 percentage
    agents_processed = Column(Integer, default=0, nullable=False)
    total_agents = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agents = relationship("Agent", back_populates="round", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Round {self.name} ({self.status})>"
