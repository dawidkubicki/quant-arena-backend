from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field
from app.models.round import RoundStatus


class MarketConfig(BaseModel):
    """Market simulation parameters"""
    initial_price: float = Field(default=100.0, ge=1.0)
    num_ticks: int = Field(default=1000, ge=100, le=10000)
    initial_equity: float = Field(default=100000.0, ge=1000.0)
    
    # Volatility and drift
    base_volatility: float = Field(default=0.02, ge=0.001, le=0.5)
    base_drift: float = Field(default=0.0001, ge=-0.01, le=0.01)
    
    # Regime parameters
    trend_probability: float = Field(default=0.3, ge=0.0, le=1.0)
    volatile_probability: float = Field(default=0.2, ge=0.0, le=1.0)
    regime_persistence: float = Field(default=0.95, ge=0.5, le=0.99)
    
    # Execution costs
    base_slippage: float = Field(default=0.001, ge=0.0, le=0.05)
    fee_rate: float = Field(default=0.001, ge=0.0, le=0.01)


class RoundConfig(BaseModel):
    """Full round configuration"""
    market: MarketConfig = Field(default_factory=MarketConfig)


class RoundCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    market_seed: int = Field(default=42, ge=0)
    config: RoundConfig = Field(default_factory=RoundConfig)


class RoundResponse(BaseModel):
    id: UUID
    name: str
    status: RoundStatus
    market_seed: int
    config: dict
    price_data: Optional[list[float]] = None
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
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
