"""
Real Market Engine using historical data from Twelve Data API.

This module replaces the synthetic GBM-based market engine with real
AAPL and SPY data for educationally accurate alpha/beta calculations.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.market_data import MarketData


@dataclass
class RealMarketState:
    """Market state at a specific tick with both AAPL and SPY data."""
    tick: int
    datetime: datetime
    
    # AAPL data (trading asset)
    aapl_open: float
    aapl_high: float
    aapl_low: float
    aapl_close: float
    aapl_volume: int
    aapl_log_return: float
    
    # SPY data (benchmark)
    spy_open: float
    spy_high: float
    spy_low: float
    spy_close: float
    spy_volume: int
    spy_log_return: float
    
    # Derived
    volatility: float  # Rolling volatility of AAPL


class RealMarketEngine:
    """
    Market engine using real historical AAPL and SPY data.
    
    Features:
    - Loads OHLCV data from PostgreSQL
    - Aligns timestamps between AAPL and SPY
    - Resamples from 1min to trading interval (5min default)
    - Calculates log returns for both instruments
    - Provides rolling volatility estimates
    """
    
    def __init__(
        self,
        db: Session,
        trading_interval: str = "5min",
        volatility_window: int = 20
    ):
        """
        Initialize the real market engine.
        
        Args:
            db: Database session
            trading_interval: Target timeframe for trading (5min, 15min, 1h)
            volatility_window: Window for rolling volatility calculation
        """
        self.db = db
        self.trading_interval = trading_interval
        self.volatility_window = volatility_window
        
        # Load and process data
        self._aapl_df: Optional[pd.DataFrame] = None
        self._spy_df: Optional[pd.DataFrame] = None
        self._aligned_df: Optional[pd.DataFrame] = None
        self._states: List[RealMarketState] = []
        
        self._load_and_process_data()
    
    def _load_data(self, symbol: str) -> pd.DataFrame:
        """Load market data for a symbol from the database."""
        bars = self.db.query(MarketData).filter(
            MarketData.symbol == symbol
        ).order_by(MarketData.datetime).all()
        
        if not bars:
            raise ValueError(f"No market data found for {symbol}. Please fetch data first.")
        
        data = [{
            "datetime": bar.datetime,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume
        } for bar in bars]
        
        df = pd.DataFrame(data)
        df.set_index("datetime", inplace=True)
        df.sort_index(inplace=True)
        
        return df
    
    def _resample_ohlcv(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        """
        Resample OHLCV data to a higher timeframe.
        
        Args:
            df: DataFrame with OHLCV columns
            interval: Target interval (5min, 15min, 1h)
        
        Returns:
            Resampled DataFrame
        """
        # Map interval strings to pandas offset aliases
        interval_map = {
            "1min": "1min",
            "5min": "5min",
            "15min": "15min",
            "30min": "30min",
            "1h": "1h"
        }
        
        offset = interval_map.get(interval, "5min")
        
        resampled = df.resample(offset).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }).dropna()
        
        return resampled
    
    def _calculate_log_returns(self, df: pd.DataFrame) -> pd.Series:
        """Calculate log returns from close prices."""
        return np.log(df["close"] / df["close"].shift(1))
    
    def _calculate_rolling_volatility(self, returns: pd.Series) -> pd.Series:
        """Calculate rolling annualized volatility."""
        # Assuming 78 5-minute bars per trading day (6.5 hours * 12 bars/hour)
        bars_per_day = 78 if self.trading_interval == "5min" else 390
        annualization_factor = np.sqrt(252 * bars_per_day)
        
        return returns.rolling(window=self.volatility_window).std() * annualization_factor
    
    def _load_and_process_data(self):
        """Load, align, resample, and calculate returns for AAPL and SPY."""
        # Load raw 1-minute data
        self._aapl_df = self._load_data("AAPL")
        self._spy_df = self._load_data("SPY")
        
        # Resample to trading interval
        aapl_resampled = self._resample_ohlcv(self._aapl_df, self.trading_interval)
        spy_resampled = self._resample_ohlcv(self._spy_df, self.trading_interval)
        
        # Align timestamps - only keep bars where both have data
        common_index = aapl_resampled.index.intersection(spy_resampled.index)
        
        if len(common_index) == 0:
            raise ValueError("No overlapping timestamps between AAPL and SPY data")
        
        aapl_aligned = aapl_resampled.loc[common_index]
        spy_aligned = spy_resampled.loc[common_index]
        
        # Calculate log returns
        aapl_returns = self._calculate_log_returns(aapl_aligned)
        spy_returns = self._calculate_log_returns(spy_aligned)
        
        # Calculate rolling volatility
        aapl_volatility = self._calculate_rolling_volatility(aapl_returns)
        
        # Build aligned DataFrame
        self._aligned_df = pd.DataFrame({
            "aapl_open": aapl_aligned["open"],
            "aapl_high": aapl_aligned["high"],
            "aapl_low": aapl_aligned["low"],
            "aapl_close": aapl_aligned["close"],
            "aapl_volume": aapl_aligned["volume"],
            "aapl_log_return": aapl_returns,
            "spy_open": spy_aligned["open"],
            "spy_high": spy_aligned["high"],
            "spy_low": spy_aligned["low"],
            "spy_close": spy_aligned["close"],
            "spy_volume": spy_aligned["volume"],
            "spy_log_return": spy_returns,
            "volatility": aapl_volatility
        })
        
        # Fill NaN values for first rows (no return yet)
        self._aligned_df["aapl_log_return"] = self._aligned_df["aapl_log_return"].fillna(0)
        self._aligned_df["spy_log_return"] = self._aligned_df["spy_log_return"].fillna(0)
        self._aligned_df["volatility"] = self._aligned_df["volatility"].fillna(0.02)  # Default 2% vol
        
        # Build states list
        self._states = []
        for tick, (dt, row) in enumerate(self._aligned_df.iterrows()):
            state = RealMarketState(
                tick=tick,
                datetime=dt.to_pydatetime(),
                aapl_open=row["aapl_open"],
                aapl_high=row["aapl_high"],
                aapl_low=row["aapl_low"],
                aapl_close=row["aapl_close"],
                aapl_volume=int(row["aapl_volume"]),
                aapl_log_return=row["aapl_log_return"],
                spy_open=row["spy_open"],
                spy_high=row["spy_high"],
                spy_low=row["spy_low"],
                spy_close=row["spy_close"],
                spy_volume=int(row["spy_volume"]),
                spy_log_return=row["spy_log_return"],
                volatility=row["volatility"]
            )
            self._states.append(state)
    
    @property
    def num_ticks(self) -> int:
        """Total number of trading bars available."""
        return len(self._states)
    
    @property
    def prices(self) -> List[float]:
        """List of AAPL close prices (for backward compatibility)."""
        return [s.aapl_close for s in self._states]
    
    @property
    def spy_returns(self) -> List[float]:
        """List of SPY log returns."""
        return [s.spy_log_return for s in self._states]
    
    @property
    def aapl_returns(self) -> List[float]:
        """List of AAPL log returns."""
        return [s.aapl_log_return for s in self._states]
    
    def get_state(self, tick: int) -> RealMarketState:
        """Get market state at a specific tick."""
        if tick < 0 or tick >= len(self._states):
            raise IndexError(f"Tick {tick} out of range [0, {len(self._states)})")
        return self._states[tick]
    
    def get_price_history(self, tick: int) -> List[float]:
        """Get AAPL price history up to and including the specified tick."""
        return [s.aapl_close for s in self._states[:tick + 1]]
    
    def get_spy_return_history(self, tick: int) -> List[float]:
        """Get SPY return history up to and including the specified tick."""
        return [s.spy_log_return for s in self._states[:tick + 1]]
    
    def get_datetime_range(self) -> Tuple[datetime, datetime]:
        """Get the datetime range of available data."""
        return self._states[0].datetime, self._states[-1].datetime
    
    def get_summary(self) -> Dict:
        """Get summary statistics about the loaded data."""
        if not self._states:
            return {"error": "No data loaded"}
        
        aapl_prices = [s.aapl_close for s in self._states]
        spy_prices = [s.spy_close for s in self._states]
        
        return {
            "num_ticks": len(self._states),
            "trading_interval": self.trading_interval,
            "start_date": self._states[0].datetime.isoformat(),
            "end_date": self._states[-1].datetime.isoformat(),
            "aapl": {
                "start_price": aapl_prices[0],
                "end_price": aapl_prices[-1],
                "return_pct": (aapl_prices[-1] / aapl_prices[0] - 1) * 100,
                "min_price": min(aapl_prices),
                "max_price": max(aapl_prices)
            },
            "spy": {
                "start_price": spy_prices[0],
                "end_price": spy_prices[-1],
                "return_pct": (spy_prices[-1] / spy_prices[0] - 1) * 100,
                "min_price": min(spy_prices),
                "max_price": max(spy_prices)
            }
        }


def check_market_data_available(db: Session) -> bool:
    """Check if required market data (AAPL and SPY) is available."""
    aapl_count = db.query(MarketData).filter(MarketData.symbol == "AAPL").count()
    spy_count = db.query(MarketData).filter(MarketData.symbol == "SPY").count()
    
    return aapl_count > 0 and spy_count > 0
