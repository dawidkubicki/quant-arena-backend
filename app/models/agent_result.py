import uuid
from datetime import datetime
from sqlalchemy import Column, Float, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class AgentResult(Base):
    """
    Stores performance results for an agent after simulation.
    
    Includes both standard metrics (Sharpe, Sortino, etc.) and
    CAPM-based alpha/beta calculations using SPY as benchmark.
    """
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
    
    # CAPM metrics (using SPY as market benchmark)
    # Alpha: Annualized excess return over what beta exposure would predict
    # Positive alpha = outperforming the market on risk-adjusted basis
    alpha = Column(Float, nullable=True)
    
    # Beta: Strategy's exposure to market risk
    # β ≈ 1: moves with market, β > 1: more volatile, β < 1: less volatile, β ≈ 0: market neutral
    beta = Column(Float, nullable=True)
    
    # Cumulative alpha over time (for visualization)
    cumulative_alpha = Column(JSONB, nullable=False, default=list)
    
    # Detailed data
    equity_curve = Column(JSONB, nullable=False, default=list)  # Array of equity values
    trades = Column(JSONB, nullable=False, default=list)  # Array of trade records
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent = relationship("Agent", back_populates="result")
    
    def __repr__(self):
        alpha_str = f"α={self.alpha:.4f}" if self.alpha else "α=N/A"
        beta_str = f"β={self.beta:.2f}" if self.beta else "β=N/A"
        return f"<AgentResult {alpha_str} {beta_str} return={self.total_return:.2f}%>"
