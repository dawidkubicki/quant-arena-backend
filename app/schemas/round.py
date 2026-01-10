from datetime import datetime
from uuid import UUID
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from app.models.round import RoundStatus


class MarketConfig(BaseModel):
    """
    Market simulation parameters.
    
    When real market data (AAPL/SPY) is available, the simulation uses actual
    historical data. The trading_interval controls the timeframe for resampling.
    
    Synthetic data parameters (initial_price, base_volatility, etc.) are only
    used as fallback when real data is not available.
    """
    # Real market data settings (primary)
    trading_interval: Literal["1min", "5min", "15min", "30min", "1h"] = Field(
        default="5min",
        description="Trading timeframe for simulation (data is resampled from 1min)"
    )
    
    # Common settings
    num_ticks: Optional[int] = Field(
        default=None,
        ge=100,
        le=100000,
        description="Max number of ticks to simulate. None = use all available data"
    )
    initial_equity: float = Field(default=100000.0, ge=1000.0)
    
    # Execution costs
    base_slippage: float = Field(default=0.001, ge=0.0, le=0.05)
    fee_rate: float = Field(default=0.001, ge=0.0, le=0.01)
    
    # Synthetic data fallback parameters (used when real data unavailable)
    initial_price: float = Field(default=100.0, ge=1.0)
    base_volatility: float = Field(default=0.02, ge=0.001, le=0.5)
    base_drift: float = Field(default=0.0001, ge=-0.01, le=0.01)
    trend_probability: float = Field(default=0.3, ge=0.0, le=1.0)
    volatile_probability: float = Field(default=0.2, ge=0.0, le=1.0)
    regime_persistence: float = Field(default=0.95, ge=0.5, le=0.99)


class RoundConfig(BaseModel):
    """Full round configuration"""
    market: MarketConfig = Field(default_factory=MarketConfig)


class RoundCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    market_seed: int = Field(default=42, ge=0)
    config: RoundConfig = Field(default_factory=RoundConfig)


class ChartDataPoint(BaseModel):
    """Data point for charts with both x and y values."""
    tick: int
    timestamp: Optional[datetime] = None  # ISO timestamp, None for synthetic data
    value: float


class RoundResponse(BaseModel):
    id: UUID
    name: str
    status: RoundStatus
    market_seed: int
    config: dict
    
    # Chart data with x-axis (tick/timestamp) and y-axis (value)
    price_data: Optional[List[ChartDataPoint]] = None  # AAPL prices over time
    spy_returns: Optional[List[ChartDataPoint]] = None  # SPY returns over time
    
    # Legacy fields (deprecated but kept for backward compatibility)
    price_data_values: Optional[List[float]] = None
    spy_returns_values: Optional[List[float]] = None
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    agent_count: int = 0
    
    class Config:
        from_attributes = True


class RoundListResponse(BaseModel):
    id: UUID
    name: str
    status: RoundStatus
    market_seed: int
    agent_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class RoundStatusResponse(BaseModel):
    id: UUID
    status: RoundStatus
    progress: int = 0  # 0-100 percentage
    agents_processed: int = 0
    total_agents: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
