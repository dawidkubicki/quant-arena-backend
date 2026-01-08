from typing import List, Dict, Any
from app.engine.strategies.base import BaseStrategy, Signal, Action
from app.utils.indicators import sma, z_score, rsi, volatility


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy
    
    Logic: When price deviates significantly from its moving average,
    bet on price returning to the mean.
    
    - Go LONG when price is significantly below SMA (oversold)
    - Go SHORT when price is significantly above SMA (overbought)
    - Go FLAT when price is near SMA
    """
    
    def generate_signal(self, prices: List[float], current_position: Action) -> Signal:
        lookback = self.strategy_params.get('lookback_window', 20)
        entry_threshold = self.strategy_params.get('entry_threshold', 2.0)
        exit_threshold = self.strategy_params.get('exit_threshold', 0.5)
        
        # Calculate indicators
        current_sma = sma(prices, lookback)
        current_zscore = z_score(prices, lookback)
        current_rsi = rsi(prices, self.signal_stack.get('rsi_window', 14))
        current_vol = volatility(prices, self.signal_stack.get('volatility_window', 20))
        
        indicators = {
            'sma': current_sma,
            'z_score': current_zscore,
            'rsi': current_rsi,
            'volatility': current_vol,
            'current_price': prices[-1] if prices else None
        }
        
        # Not enough data
        if current_zscore is None or current_sma is None:
            return Signal(
                action=Action.FLAT,
                confidence=0.0,
                reason="Insufficient data for signal generation",
                indicators=indicators
            )
        
        # Generate signal based on z-score
        if current_zscore < -entry_threshold:
            # Price significantly below SMA - expect reversion up
            confidence = min(abs(current_zscore) / 4.0, 1.0)
            signal = Signal(
                action=Action.LONG,
                confidence=confidence,
                reason=f"Price oversold (z-score: {current_zscore:.2f})",
                indicators=indicators
            )
        elif current_zscore > entry_threshold:
            # Price significantly above SMA - expect reversion down
            confidence = min(abs(current_zscore) / 4.0, 1.0)
            signal = Signal(
                action=Action.SHORT,
                confidence=confidence,
                reason=f"Price overbought (z-score: {current_zscore:.2f})",
                indicators=indicators
            )
        elif abs(current_zscore) < exit_threshold:
            # Price near mean - exit positions
            signal = Signal(
                action=Action.FLAT,
                confidence=0.8,
                reason=f"Price near mean (z-score: {current_zscore:.2f})",
                indicators=indicators
            )
        else:
            # Hold current position
            signal = Signal(
                action=current_position,
                confidence=0.5,
                reason="No clear signal, holding position",
                indicators=indicators
            )
        
        # Apply additional filters
        return self.apply_signal_filters(signal, indicators)
