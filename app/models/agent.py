import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class StrategyType(str, PyEnum):
    MEAN_REVERSION = "MEAN_REVERSION"
    TREND_FOLLOWING = "TREND_FOLLOWING"
    MOMENTUM = "MOMENTUM"
    GHOST = "GHOST"  # Benchmark agent


class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    round_id = Column(UUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False)
    strategy_type = Column(Enum(StrategyType), nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="agents")
    round = relationship("Round", back_populates="agents")
    result = relationship("AgentResult", back_populates="agent", uselist=False, cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="agent", cascade="all, delete-orphan", passive_deletes=True)
    
    # Unique constraint: one agent per user per round
    __table_args__ = (
        UniqueConstraint('user_id', 'round_id', name='unique_user_round'),
    )
    
    def __repr__(self):
        return f"<Agent {self.strategy_type} by user {self.user_id}>"
