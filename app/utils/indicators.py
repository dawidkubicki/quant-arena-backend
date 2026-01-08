import numpy as np
from typing import List, Optional


def sma(prices: List[float], window: int) -> Optional[float]:
    """
    Calculate Simple Moving Average.
    Returns None if not enough data.
    """
    if len(prices) < window:
        return None
    return np.mean(prices[-window:])


def ema(prices: List[float], window: int) -> Optional[float]:
    """
    Calculate Exponential Moving Average.
    Returns None if not enough data.
    """
    if len(prices) < window:
        return None
    
    multiplier = 2 / (window + 1)
    ema_value = prices[0]
    
    for price in prices[1:]:
        ema_value = (price - ema_value) * multiplier + ema_value
    
    return ema_value


def rsi(prices: List[float], window: int = 14) -> Optional[float]:
    """
    Calculate Relative Strength Index (RSI).
    Returns value between 0 and 100.
    Returns None if not enough data.
    """
    if len(prices) < window + 1:
        return None
    
    # Calculate price changes
    deltas = np.diff(prices[-(window + 1):])
    
    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi_value = 100 - (100 / (1 + rs))
    
    return rsi_value


def atr(highs: List[float], lows: List[float], closes: List[float], window: int = 14) -> Optional[float]:
    """
    Calculate Average True Range (ATR).
    For simplicity with single price series, we estimate using price volatility.
    Returns None if not enough data.
    """
    if len(closes) < window + 1:
        return None
    
    # Simplified ATR using close prices only
    # True range approximated as daily range
    prices = np.array(closes[-(window + 1):])
    returns = np.abs(np.diff(prices) / prices[:-1])
    
    return np.mean(returns) * prices[-1]


def atr_from_prices(prices: List[float], window: int = 14) -> Optional[float]:
    """
    Estimate ATR from price series only (simplified version).
    """
    if len(prices) < window + 1:
        return None
    
    price_array = np.array(prices[-(window + 1):])
    abs_changes = np.abs(np.diff(price_array))
    
    return np.mean(abs_changes)


def momentum(prices: List[float], window: int = 14) -> Optional[float]:
    """
    Calculate price momentum (rate of change).
    Returns percentage change over the window.
    """
    if len(prices) < window + 1:
        return None
    
    return (prices[-1] - prices[-window - 1]) / prices[-window - 1] * 100


def bollinger_bands(
    prices: List[float], 
    window: int = 20, 
    num_std: float = 2.0
) -> Optional[tuple]:
    """
    Calculate Bollinger Bands.
    Returns (upper_band, middle_band, lower_band) or None if not enough data.
    """
    if len(prices) < window:
        return None
    
    middle = np.mean(prices[-window:])
    std = np.std(prices[-window:])
    
    upper = middle + num_std * std
    lower = middle - num_std * std
    
    return (upper, middle, lower)


def volatility(prices: List[float], window: int = 20) -> Optional[float]:
    """
    Calculate realized volatility (annualized standard deviation of returns).
    """
    if len(prices) < window + 1:
        return None
    
    returns = np.diff(np.log(prices[-window - 1:]))
    return np.std(returns) * np.sqrt(252)


def z_score(prices: List[float], window: int = 20) -> Optional[float]:
    """
    Calculate z-score of current price relative to recent prices.
    """
    if len(prices) < window:
        return None
    
    mean = np.mean(prices[-window:])
    std = np.std(prices[-window:])
    
    if std == 0:
        return 0.0
    
    return (prices[-1] - mean) / std


class IndicatorCalculator:
    """Helper class to calculate multiple indicators at once."""
    
    def __init__(self, prices: List[float]):
        self.prices = prices
    
    def calculate_all(
        self,
        sma_window: int = 20,
        rsi_window: int = 14,
        volatility_window: int = 20,
        momentum_window: int = 14
    ) -> dict:
        """Calculate all indicators and return as dict."""
        return {
            'sma': sma(self.prices, sma_window),
            'ema': ema(self.prices, sma_window),
            'rsi': rsi(self.prices, rsi_window),
            'volatility': volatility(self.prices, volatility_window),
            'momentum': momentum(self.prices, momentum_window),
            'z_score': z_score(self.prices, sma_window),
            'atr': atr_from_prices(self.prices, rsi_window),
            'current_price': self.prices[-1] if self.prices else None
        }
