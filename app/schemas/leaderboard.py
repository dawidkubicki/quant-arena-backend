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


class GlobalLeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    nickname: str
    color: str
    icon: str
    
    # Aggregate statistics
    total_rounds: int  # Number of rounds participated in
    avg_sharpe_ratio: Optional[float]  # Average Sharpe ratio across all rounds
    best_sharpe_ratio: Optional[float]  # Best single-round Sharpe ratio
    avg_total_return: float  # Average total return across all rounds
    best_total_return: float  # Best single-round total return
    avg_alpha: Optional[float]  # Average alpha across all rounds
    best_alpha: Optional[float]  # Best single-round alpha
    
    # Win statistics
    first_place_count: int  # Number of 1st place finishes
    top_3_count: int  # Number of top 3 finishes
    top_10_count: int  # Number of top 10 finishes
    win_rate: float  # Percentage of top 3 finishes
    
    # Overall performance score (weighted metric)
    performance_score: float


class GlobalLeaderboardResponse(BaseModel):
    entries: list[GlobalLeaderboardEntry]
    total_users: int
    total_rounds_analyzed: int
    
    # Summary stats
    highest_avg_sharpe: Optional[float] = None
    highest_avg_return: Optional[float] = None
    highest_avg_alpha: Optional[float] = None
    most_rounds_participated: int = 0
