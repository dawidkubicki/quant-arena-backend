from typing import List, Dict, Any
from app.engine.strategies.base import BaseStrategy, Signal, Action
from app.utils.indicators import sma, ema, atr_from_prices, volatility


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy (LONG-ONLY)
    
    Logic: Follow uptrends using moving average crossovers. This strategy can only go long.
    
    Strategy Parameters:
    - fast_window: Fast EMA period (shorter = more responsive)
    - slow_window: Slow EMA period (longer = smoother trend)
    - atr_multiplier: ATR multiplier for volatility-adjusted signals
    
    Signal Generation (Long-Only):
    - Go LONG when fast EMA crosses above slow EMA (bullish crossover)
    - Go FLAT (exit) when fast EMA crosses below slow EMA (bearish crossover)
    - Stay in long position until bearish crossover occurs
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.prev_fast_ma = None
        self.prev_slow_ma = None
    
    def generate_signal(self, prices: List[float], current_position: Action) -> Signal:
        # Strategy-specific parameters
        fast_window = self.strategy_params.get('fast_window', 10)
        slow_window = self.strategy_params.get('slow_window', 30)
        atr_multiplier = self.strategy_params.get('atr_multiplier', 2.0)
        
        # Calculate core strategy indicators
        fast_ma = ema(prices, fast_window)
        slow_ma = ema(prices, slow_window)
        current_atr = atr_from_prices(prices, 14)
        
        # Calculate indicators for signal_stack filters
        filter_sma = sma(prices, self.signal_stack.get('sma_filter_window', 50))
        current_vol = volatility(prices, self.signal_stack.get('volatility_window', 20))
        
        indicators = {
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'sma': filter_sma,  # For trend filter
            'atr': current_atr,
            'volatility': current_vol,
            'current_price': prices[-1] if prices else None
        }
        
        # Not enough data
        if fast_ma is None or slow_ma is None:
            self.prev_fast_ma = fast_ma
            self.prev_slow_ma = slow_ma
            return Signal(
                action=Action.FLAT,
                confidence=0.0,
                reason="Insufficient data for signal generation",
                indicators=indicators
            )
        
        # Detect crossover
        crossover_up = False
        crossover_down = False
        
        if self.prev_fast_ma is not None and self.prev_slow_ma is not None:
            # Bullish crossover: fast MA crosses above slow MA
            if self.prev_fast_ma <= self.prev_slow_ma and fast_ma > slow_ma:
                crossover_up = True
            # Bearish crossover: fast MA crosses below slow MA
            elif self.prev_fast_ma >= self.prev_slow_ma and fast_ma < slow_ma:
                crossover_down = True
        
        # Update previous values
        self.prev_fast_ma = fast_ma
        self.prev_slow_ma = slow_ma
        
        # Generate signal (LONG-ONLY)
        if crossover_up:
            # Calculate trend strength
            trend_strength = (fast_ma - slow_ma) / slow_ma if slow_ma else 0
            confidence = min(abs(trend_strength) * 50 + 0.6, 1.0)
            signal = Signal(
                action=Action.LONG,
                confidence=confidence,
                reason=f"Bullish crossover (fast MA: {fast_ma:.2f}, slow MA: {slow_ma:.2f})",
                indicators=indicators
            )
        elif crossover_down and current_position == Action.LONG:
            # Bearish crossover - EXIT long position
            trend_strength = (slow_ma - fast_ma) / slow_ma if slow_ma else 0
            confidence = min(abs(trend_strength) * 50 + 0.6, 1.0)
            signal = Signal(
                action=Action.FLAT,
                confidence=confidence,
                reason=f"Bearish crossover, exit long (fast MA: {fast_ma:.2f}, slow MA: {slow_ma:.2f})",
                indicators=indicators
            )
        elif fast_ma > slow_ma and current_position != Action.LONG:
            # In uptrend but not long - consider entry
            confidence = 0.4
            signal = Signal(
                action=Action.LONG,
                confidence=confidence,
                reason="Uptrend continuation, entering long",
                indicators=indicators
            )
        elif fast_ma > slow_ma and current_position == Action.LONG:
            # In uptrend and already long - hold
            signal = Signal(
                action=Action.LONG,
                confidence=0.5,
                reason="Holding long in uptrend",
                indicators=indicators
            )
        elif fast_ma < slow_ma and current_position == Action.LONG:
            # In downtrend with long position - exit
            signal = Signal(
                action=Action.FLAT,
                confidence=0.5,
                reason="Downtrend detected, exiting long",
                indicators=indicators
            )
        else:
            # No position in downtrend - stay flat
            signal = Signal(
                action=Action.FLAT,
                confidence=0.4,
                reason="Downtrend, staying flat (long-only)",
                indicators=indicators
            )
        
        # Apply filters and enforce long-only
        filtered_signal = self.apply_signal_filters(signal, indicators)
        return self.enforce_long_only(filtered_signal)
