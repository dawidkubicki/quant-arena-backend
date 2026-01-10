from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class TradeResponse(BaseModel):
    """
    Response schema for a single trade execution.
    
    Since strategies are LONG-ONLY, the action will be one of:
    - OPEN_LONG: Bought/entered a long position
    - CLOSE_LONG: Sold/exited the long position
    """
    id: UUID
    agent_id: UUID
    tick: int  # X-axis: tick number
    timestamp: datetime | None  # X-axis: market timestamp (None for synthetic data)
    action: str  # OPEN_LONG, CLOSE_LONG (long-only strategies)
    price: float  # Y-axis: market price
    executed_price: float  # Y-axis: actual execution price
    size: float
    cost: float
    pnl: float  # Realized P&L (only non-zero for CLOSE trades)
    equity_after: float
    reason: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CompletedTradeResponse(BaseModel):
    """
    A completed round-trip trade (entry + exit paired together).
    
    This pairs an OPEN_LONG with its corresponding CLOSE_LONG for clear
    visualization of each trade's full lifecycle.
    """
    trade_number: int  # Sequential trade number (1, 2, 3, ...)
    
    # Entry (OPEN_LONG)
    entry_tick: int
    entry_timestamp: datetime | None
    entry_price: float
    entry_executed_price: float
    entry_reason: str | None
    
    # Exit (CLOSE_LONG)
    exit_tick: int
    exit_timestamp: datetime | None
    exit_price: float
    exit_executed_price: float
    exit_reason: str | None
    
    # Trade details
    size: float
    total_cost: float  # Combined fees (entry + exit)
    
    # Performance
    pnl: float  # Realized P&L
    return_pct: float  # Return percentage: (exit - entry) / entry * 100
    duration_ticks: int  # How many ticks the position was held
    
    # Status
    is_winner: bool
    
    class Config:
        from_attributes = True


class TradeListResponse(BaseModel):
    """Response schema for a list of individual trades with metadata"""
    trades: list[TradeResponse]
    total_trades: int
    total_pnl: float
    winning_trades: int
    losing_trades: int
    win_rate: float  # Percentage
    
    class Config:
        from_attributes = True


class CompletedTradesResponse(BaseModel):
    """
    Response schema for completed round-trip trades.
    
    Provides a clear view of each trade's entry and exit, making it easy
    to display trade history on the frontend.
    """
    completed_trades: list[CompletedTradeResponse]
    
    # Currently open position (if any)
    has_open_position: bool
    open_position: Optional[dict] = None  # Entry details if position is open
    
    # Summary statistics
    total_completed_trades: int
    total_pnl: float
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_return_pct: float
    avg_duration_ticks: float
    best_trade_pnl: float
    worst_trade_pnl: float
    
    class Config:
        from_attributes = True
