from datetime import datetime
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.agent import StrategyType


class ChartDataPoint(BaseModel):
    """Data point for charts with both x and y values."""
    tick: int
    timestamp: Optional[datetime] = None  # ISO timestamp, None for synthetic data
    value: float


class StrategyParams(BaseModel):
    """
    Strategy-specific parameters.
    
    All strategies are LONG-ONLY: they can only buy (go long) and sell (exit).
    No short selling is supported.
    
    Each strategy type uses only its relevant parameters:
    - MEAN_REVERSION: lookback_window, entry_threshold, exit_threshold
    - TREND_FOLLOWING: fast_window, slow_window, atr_multiplier
    - MOMENTUM: momentum_window, rsi_window, rsi_overbought, rsi_oversold
    """
    
    # === MEAN REVERSION ===
    # Bets on price returning to average - buys dips, sells rallies
    lookback_window: int = Field(
        default=20, ge=5, le=200,
        description="Window for calculating mean price (z-score baseline)"
    )
    entry_threshold: float = Field(
        default=2.0, ge=0.5, le=5.0,
        description="Z-score threshold to enter position (how far from mean)"
    )
    exit_threshold: float = Field(
        default=0.5, ge=0.0, le=2.0,
        description="Z-score threshold to exit position (return to mean)"
    )
    
    # === TREND FOLLOWING ===
    # Follows the trend using moving average crossovers
    fast_window: int = Field(
        default=10, ge=3, le=50,
        description="Fast EMA period (shorter = more responsive)"
    )
    slow_window: int = Field(
        default=30, ge=10, le=200,
        description="Slow EMA period (longer = smoother trend)"
    )
    atr_multiplier: float = Field(
        default=2.0, ge=0.5, le=5.0,
        description="ATR multiplier for volatility-adjusted signals"
    )
    
    # === MOMENTUM ===
    # Follows price momentum - buys winners, sells losers
    momentum_window: int = Field(
        default=14, ge=5, le=100,
        description="Lookback period for momentum calculation"
    )
    rsi_window: int = Field(
        default=14, ge=5, le=50,
        description="RSI calculation period"
    )
    rsi_overbought: float = Field(
        default=70.0, ge=50.0, le=95.0,
        description="RSI level indicating overbought (avoid new longs)"
    )
    rsi_oversold: float = Field(
        default=30.0, ge=5.0, le=50.0,
        description="RSI level indicating oversold (potential long entry)"
    )


class SignalStack(BaseModel):
    """
    Universal signal filters applied AFTER any strategy generates a signal.
    
    These filters can reduce confidence or block signals based on market conditions.
    They apply to ALL strategy types equally.
    
    Note: Strategies are LONG-ONLY (buy then sell, no shorting).
    """
    
    # === SMA TREND FILTER ===
    # Only allow longs when price is above SMA (uptrend)
    # Reduces confidence for long entries when price is below SMA
    use_sma_trend_filter: bool = Field(
        default=False,
        description="Reduce confidence for longs when price is below SMA"
    )
    sma_filter_window: int = Field(
        default=50, ge=10, le=200,
        description="SMA period for trend filter (longer = stronger trend)"
    )
    
    # === VOLATILITY FILTER ===
    # Reduce confidence or skip signals when volatility is high
    use_volatility_filter: bool = Field(
        default=False,
        description="Reduce signal confidence in high volatility environments"
    )
    volatility_window: int = Field(
        default=20, ge=5, le=100,
        description="Window for volatility calculation"
    )
    volatility_threshold: float = Field(
        default=1.5, ge=0.5, le=5.0,
        description="Volatility multiplier threshold (higher = more permissive)"
    )


class RiskParams(BaseModel):
    """Risk management parameters"""
    position_size_pct: float = Field(default=10.0, ge=1.0, le=100.0)
    max_leverage: float = Field(default=1.0, ge=1.0, le=5.0)
    stop_loss_pct: float = Field(default=5.0, ge=0.5, le=50.0)
    take_profit_pct: float = Field(default=10.0, ge=1.0, le=100.0)
    max_drawdown_kill: float = Field(default=20.0, ge=5.0, le=100.0)


class AgentConfig(BaseModel):
    """Full agent configuration"""
    strategy_params: StrategyParams = Field(default_factory=StrategyParams)
    signal_stack: SignalStack = Field(default_factory=SignalStack)
    risk_params: RiskParams = Field(default_factory=RiskParams)


class AgentCreate(BaseModel):
    strategy_type: StrategyType
    config: AgentConfig = Field(default_factory=AgentConfig)


class AgentUpdate(BaseModel):
    strategy_type: Optional[StrategyType] = None
    config: Optional[AgentConfig] = None


class TradeRecord(BaseModel):
    """Individual trade record (long-only: OPEN_LONG or CLOSE_LONG)"""
    tick: int
    action: str  # OPEN_LONG, CLOSE_LONG (long-only strategies)
    price: float
    size: float
    pnl: float
    equity_after: float


class AgentResultResponse(BaseModel):
    id: UUID
    agent_id: UUID
    final_equity: float
    total_return: float
    sharpe_ratio: Optional[float]
    max_drawdown: float
    calmar_ratio: Optional[float]
    total_trades: int
    win_rate: Optional[float]
    survival_time: int
    
    # Chart data with x-axis (tick/timestamp) and y-axis (value)
    equity_curve: Optional[List[ChartDataPoint]] = None  # Equity over time
    cumulative_alpha: Optional[List[ChartDataPoint]] = None  # Alpha accumulation over time
    
    # Legacy fields (deprecated but kept for backward compatibility)
    equity_curve_values: Optional[list[float]] = None
    cumulative_alpha_values: Optional[list[float]] = None
    
    trades: list[dict]
    # CAPM metrics (alpha/beta relative to SPY)
    alpha: Optional[float] = None  # Annualized excess return
    beta: Optional[float] = None   # Market exposure
    created_at: datetime
    
    class Config:
        from_attributes = True


class AgentResponse(BaseModel):
    id: UUID
    user_id: UUID
    round_id: UUID
    strategy_type: StrategyType
    config: dict
    created_at: datetime
    result: Optional[AgentResultResponse] = None
    user_nickname: Optional[str] = None
    user_color: Optional[str] = None
    
    class Config:
        from_attributes = True
