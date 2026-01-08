from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field
from app.models.agent import StrategyType


class StrategyParams(BaseModel):
    """Strategy-specific parameters"""
    # Mean Reversion
    lookback_window: int = Field(default=20, ge=5, le=200)
    entry_threshold: float = Field(default=2.0, ge=0.5, le=5.0)
    exit_threshold: float = Field(default=0.5, ge=0.0, le=2.0)
    
    # Trend Following
    fast_window: int = Field(default=10, ge=3, le=50)
    slow_window: int = Field(default=30, ge=10, le=200)
    atr_multiplier: float = Field(default=2.0, ge=0.5, le=5.0)
    
    # Momentum
    momentum_window: int = Field(default=14, ge=5, le=100)
    rsi_window: int = Field(default=14, ge=5, le=50)
    rsi_overbought: float = Field(default=70.0, ge=50.0, le=95.0)
    rsi_oversold: float = Field(default=30.0, ge=5.0, le=50.0)


class SignalStack(BaseModel):
    """Common signal configuration"""
    use_sma: bool = Field(default=True)
    sma_window: int = Field(default=20, ge=5, le=200)
    
    use_rsi: bool = Field(default=True)
    rsi_window: int = Field(default=14, ge=5, le=50)
    rsi_overbought: float = Field(default=70.0, ge=50.0, le=95.0)
    rsi_oversold: float = Field(default=30.0, ge=5.0, le=50.0)
    
    use_volatility_filter: bool = Field(default=False)
    volatility_window: int = Field(default=20, ge=5, le=100)
    volatility_threshold: float = Field(default=1.5, ge=0.5, le=5.0)


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
    tick: int
    action: str  # LONG, SHORT, FLAT
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
    equity_curve: list[float]
    trades: list[dict]
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
