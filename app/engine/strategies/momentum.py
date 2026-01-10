from typing import List, Dict, Any
from app.engine.strategies.base import BaseStrategy, Signal, Action
from app.utils.indicators import momentum, rsi, sma, volatility


class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy (LONG-ONLY)
    
    Logic: Buy strength based on price momentum and RSI. This strategy can only go long.
    
    Signal Generation (Long-Only):
    - Go LONG when momentum is positive and RSI is not overbought
    - Go FLAT (exit) when momentum turns negative or RSI is overbought
    - Use RSI to avoid buying at tops
    """
    
    def generate_signal(self, prices: List[float], current_position: Action) -> Signal:
        momentum_window = self.strategy_params.get('momentum_window', 14)
        rsi_window = self.strategy_params.get('rsi_window', 14)
        rsi_overbought = self.strategy_params.get('rsi_overbought', 70)
        rsi_oversold = self.strategy_params.get('rsi_oversold', 30)
        
        # Calculate indicators
        current_momentum = momentum(prices, momentum_window)
        current_rsi = rsi(prices, rsi_window)
        # SMA for signal_stack trend filter (if enabled)
        current_sma = sma(prices, self.signal_stack.get('sma_filter_window', 50))
        current_vol = volatility(prices, self.signal_stack.get('volatility_window', 20))
        
        indicators = {
            'momentum': current_momentum,
            'rsi': current_rsi,
            'sma': current_sma,
            'volatility': current_vol,
            'current_price': prices[-1] if prices else None
        }
        
        # Not enough data
        if current_momentum is None or current_rsi is None:
            return Signal(
                action=Action.FLAT,
                confidence=0.0,
                reason="Insufficient data for signal generation",
                indicators=indicators
            )
        
        # Strong positive momentum + RSI not overbought -> GO LONG
        if current_momentum > 2.0 and current_rsi < rsi_overbought:
            # Scale confidence with momentum strength
            confidence = min(current_momentum / 10.0 + 0.4, 1.0)
            signal = Signal(
                action=Action.LONG,
                confidence=confidence,
                reason=f"Strong positive momentum ({current_momentum:.2f}%), RSI: {current_rsi:.1f}",
                indicators=indicators
            )
        # Strong negative momentum -> EXIT any long position
        elif current_momentum < -2.0 and current_position == Action.LONG:
            confidence = min(abs(current_momentum) / 10.0 + 0.4, 1.0)
            signal = Signal(
                action=Action.FLAT,
                confidence=confidence,
                reason=f"Negative momentum, exit signal ({current_momentum:.2f}%), RSI: {current_rsi:.1f}",
                indicators=indicators
            )
        # RSI overbought - potential reversal, exit long
        elif current_rsi > rsi_overbought and current_position == Action.LONG:
            signal = Signal(
                action=Action.FLAT,
                confidence=0.7,
                reason=f"RSI overbought ({current_rsi:.1f}), exiting long",
                indicators=indicators
            )
        # Weak or negative momentum - stay flat or exit
        elif current_momentum < 1.0 and current_position == Action.LONG:
            signal = Signal(
                action=Action.FLAT,
                confidence=0.6,
                reason=f"Weak/negative momentum ({current_momentum:.2f}%), exiting long",
                indicators=indicators
            )
        # Holding long with moderate positive momentum
        elif current_position == Action.LONG and current_momentum > 0:
            signal = Signal(
                action=Action.LONG,
                confidence=0.5,
                reason=f"Holding long, momentum still positive ({current_momentum:.2f}%)",
                indicators=indicators
            )
        else:
            # No position or waiting for entry
            signal = Signal(
                action=Action.FLAT,
                confidence=0.4,
                reason=f"No entry signal, momentum: {current_momentum:.2f}%",
                indicators=indicators
            )
        
        # Apply filters and enforce long-only
        filtered_signal = self.apply_signal_filters(signal, indicators)
        return self.enforce_long_only(filtered_signal)
