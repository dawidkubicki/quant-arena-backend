from typing import List, Dict, Any
from app.engine.strategies.base import BaseStrategy, Signal, Action
from app.utils.indicators import sma, ema, atr_from_prices, rsi, volatility


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend Following Strategy
    
    Logic: Follow the trend using moving average crossovers.
    
    - Go LONG when fast MA crosses above slow MA (uptrend)
    - Go SHORT when fast MA crosses below slow MA (downtrend)
    - Use ATR for position sizing and stop placement
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.prev_fast_ma = None
        self.prev_slow_ma = None
    
    def generate_signal(self, prices: List[float], current_position: Action) -> Signal:
        fast_window = self.strategy_params.get('fast_window', 10)
        slow_window = self.strategy_params.get('slow_window', 30)
        atr_multiplier = self.strategy_params.get('atr_multiplier', 2.0)
        
        # Calculate indicators
        fast_ma = ema(prices, fast_window)
        slow_ma = ema(prices, slow_window)
        current_atr = atr_from_prices(prices, 14)
        current_rsi = rsi(prices, self.signal_stack.get('rsi_window', 14))
        current_vol = volatility(prices, self.signal_stack.get('volatility_window', 20))
        
        indicators = {
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'atr': current_atr,
            'rsi': current_rsi,
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
        
        # Generate signal
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
        elif crossover_down:
            trend_strength = (slow_ma - fast_ma) / slow_ma if slow_ma else 0
            confidence = min(abs(trend_strength) * 50 + 0.6, 1.0)
            signal = Signal(
                action=Action.SHORT,
                confidence=confidence,
                reason=f"Bearish crossover (fast MA: {fast_ma:.2f}, slow MA: {slow_ma:.2f})",
                indicators=indicators
            )
        elif fast_ma > slow_ma and current_position != Action.LONG:
            # In uptrend but not long - consider entry
            confidence = 0.4
            signal = Signal(
                action=Action.LONG,
                confidence=confidence,
                reason="Uptrend continuation",
                indicators=indicators
            )
        elif fast_ma < slow_ma and current_position != Action.SHORT:
            # In downtrend but not short - consider entry
            confidence = 0.4
            signal = Signal(
                action=Action.SHORT,
                confidence=confidence,
                reason="Downtrend continuation",
                indicators=indicators
            )
        else:
            # Hold current position
            signal = Signal(
                action=current_position,
                confidence=0.5,
                reason="Holding current trend position",
                indicators=indicators
            )
        
        return self.apply_signal_filters(signal, indicators)
