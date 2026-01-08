import uuid
from datetime import datetime
from sqlalchemy import Column, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class AgentResult(Base):
    __tablename__ = "agent_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Performance metrics
    final_equity = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)  # Percentage
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=False)  # Percentage (positive value)
    calmar_ratio = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=True)  # Percentage
    survival_time = Column(Integer, nullable=False)  # Ticks survived
    
    # Detailed data
    equity_curve = Column(JSONB, nullable=False, default=list)  # Array of equity values
    trades = Column(JSONB, nullable=False, default=list)  # Array of trade records
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="result")
    
    def __repr__(self):
        return f"<AgentResult sharpe={self.sharpe_ratio:.2f} return={self.total_return:.2f}%>"
