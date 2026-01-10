from typing import List, Dict, Any
from app.engine.strategies.base import BaseStrategy, Signal, Action
from app.utils.indicators import sma, z_score, volatility


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Strategy (LONG-ONLY)
    
    Logic: When price deviates significantly from its moving average,
    bet on price returning to the mean. This strategy can only go long.
    
    Strategy Parameters:
    - lookback_window: Window for calculating mean price (z-score baseline)
    - entry_threshold: Z-score threshold to enter position
    - exit_threshold: Z-score threshold to exit position
    
    Signal Generation (Long-Only):
    - Go LONG when price is significantly below SMA (z-score < -entry_threshold)
    - Go FLAT (exit) when price is overbought (z-score > entry_threshold) or returns to mean
    - Hold position in neutral zones
    """
    
    def generate_signal(self, prices: List[float], current_position: Action) -> Signal:
        # Strategy-specific parameters
        lookback = self.strategy_params.get('lookback_window', 20)
        entry_threshold = self.strategy_params.get('entry_threshold', 2.0)
        exit_threshold = self.strategy_params.get('exit_threshold', 0.5)
        
        # Calculate core strategy indicators
        strategy_sma = sma(prices, lookback)  # Used for z-score calculation
        current_zscore = z_score(prices, lookback)
        
        # Calculate indicators for signal_stack filters
        filter_sma = sma(prices, self.signal_stack.get('sma_filter_window', 50))
        current_vol = volatility(prices, self.signal_stack.get('volatility_window', 20))
        
        indicators = {
            'sma': filter_sma,  # For trend filter
            'strategy_sma': strategy_sma,  # For display/debugging
            'z_score': current_zscore,
            'volatility': current_vol,
            'current_price': prices[-1] if prices else None
        }
        
        # Not enough data
        if current_zscore is None or strategy_sma is None:
            return Signal(
                action=Action.FLAT,
                confidence=0.0,
                reason="Insufficient data for signal generation",
                indicators=indicators
            )
        
        # Generate signal based on z-score (LONG-ONLY)
        if current_zscore < -entry_threshold:
            # Price significantly below SMA - expect reversion up, go LONG
            confidence = min(abs(current_zscore) / 4.0, 1.0)
            signal = Signal(
                action=Action.LONG,
                confidence=confidence,
                reason=f"Price oversold (z-score: {current_zscore:.2f})",
                indicators=indicators
            )
        elif current_zscore > entry_threshold:
            # Price significantly above SMA - overbought, EXIT any long position
            confidence = min(abs(current_zscore) / 4.0, 1.0)
            signal = Signal(
                action=Action.FLAT,
                confidence=confidence,
                reason=f"Price overbought, exit signal (z-score: {current_zscore:.2f})",
                indicators=indicators
            )
        elif abs(current_zscore) < exit_threshold and current_position == Action.LONG:
            # Price near mean - exit long position (take profit)
            signal = Signal(
                action=Action.FLAT,
                confidence=0.8,
                reason=f"Price reverted to mean, exit long (z-score: {current_zscore:.2f})",
                indicators=indicators
            )
        elif current_position == Action.LONG:
            # In a long position, hold until exit condition
            signal = Signal(
                action=Action.LONG,
                confidence=0.5,
                reason="Holding long position, waiting for exit signal",
                indicators=indicators
            )
        else:
            # No position, wait for entry signal
            signal = Signal(
                action=Action.FLAT,
                confidence=0.5,
                reason="No clear entry signal, staying flat",
                indicators=indicators
            )
        
        # Apply additional filters and enforce long-only
        filtered_signal = self.apply_signal_filters(signal, indicators)
        return self.enforce_long_only(filtered_signal)
