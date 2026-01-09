from uuid import UUID
from typing import Optional
from pydantic import BaseModel
from app.models.agent import StrategyType


class LeaderboardEntry(BaseModel):
    rank: int
    agent_id: UUID
    user_id: UUID
    nickname: str
    color: str
    icon: str
    strategy_type: StrategyType
    
    # Metrics
    final_equity: float
    total_return: float
    sharpe_ratio: Optional[float]
    max_drawdown: float
    calmar_ratio: Optional[float]
    win_rate: Optional[float]
    total_trades: int
    survival_time: int
    
    # CAPM metrics (alpha/beta relative to SPY benchmark)
    alpha: Optional[float] = None  # Annualized excess return over market
    beta: Optional[float] = None   # Market exposure coefficient
    
    # For highlighting
    is_ghost: bool = False


class LeaderboardResponse(BaseModel):
    round_id: UUID
    round_name: str
    entries: list[LeaderboardEntry]
    total_participants: int
    
    # Summary stats
    best_sharpe: Optional[float] = None
    best_return: Optional[float] = None
    lowest_drawdown: Optional[float] = None
    average_survival: Optional[float] = None
