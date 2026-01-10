import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Trade(Base):
    """
    Stores individual buy/sell transactions for each agent.
    
    Each trade record represents a single execution event (opening or closing a position).
    This allows detailed trade-by-trade analysis and charting in the frontend.
    """
    __tablename__ = "trades"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    # Trade details
    tick = Column(Integer, nullable=False)  # When the trade occurred (0-indexed)
    timestamp = Column(DateTime, nullable=True)  # Market timestamp (None for synthetic data)
    action = Column(String(20), nullable=False)  # OPEN_LONG, CLOSE_LONG, OPEN_SHORT, CLOSE_SHORT
    price = Column(Float, nullable=False)  # Market price at execution
    executed_price = Column(Float, nullable=False)  # Actual price after slippage
    size = Column(Float, nullable=False)  # Position size
    cost = Column(Float, nullable=False)  # Transaction fees
    pnl = Column(Float, nullable=False, default=0.0)  # Realized P&L (0 for opening trades)
    equity_after = Column(Float, nullable=False)  # Total equity after trade
    reason = Column(String(200), nullable=True)  # Why the trade was made
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships - passive_deletes=True lets PostgreSQL handle CASCADE deletion
    agent = relationship("Agent", back_populates="trades", passive_deletes=True)
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_trades_agent_id', 'agent_id'),
        Index('idx_trades_agent_tick', 'agent_id', 'tick'),
    )
    
    def __repr__(self):
        return f"<Trade {self.action} @ {self.executed_price:.2f} tick={self.tick}>"
