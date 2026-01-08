from typing import List, Dict, Any
from app.engine.strategies.base import BaseStrategy, Signal, Action
from app.utils.indicators import momentum, rsi, sma, volatility


class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy
    
    Logic: Buy strength, sell weakness based on price momentum and RSI.
    
    - Go LONG when momentum is positive and RSI is not overbought
    - Go SHORT when momentum is negative and RSI is not oversold
    - Use RSI to avoid buying at tops and selling at bottoms
    """
    
    def generate_signal(self, prices: List[float], current_position: Action) -> Signal:
        momentum_window = self.strategy_params.get('momentum_window', 14)
        rsi_window = self.strategy_params.get('rsi_window', 14)
        rsi_overbought = self.strategy_params.get('rsi_overbought', 70)
        rsi_oversold = self.strategy_params.get('rsi_oversold', 30)
        
        # Calculate indicators
        current_momentum = momentum(prices, momentum_window)
        current_rsi = rsi(prices, rsi_window)
        current_sma = sma(prices, self.signal_stack.get('sma_window', 20))
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
        
        # Strong positive momentum + RSI not overbought
        if current_momentum > 2.0 and current_rsi < rsi_overbought:
            # Scale confidence with momentum strength
            confidence = min(current_momentum / 10.0 + 0.4, 1.0)
            signal = Signal(
                action=Action.LONG,
                confidence=confidence,
                reason=f"Strong positive momentum ({current_momentum:.2f}%), RSI: {current_rsi:.1f}",
                indicators=indicators
            )
        # Strong negative momentum + RSI not oversold
        elif current_momentum < -2.0 and current_rsi > rsi_oversold:
            confidence = min(abs(current_momentum) / 10.0 + 0.4, 1.0)
            signal = Signal(
                action=Action.SHORT,
                confidence=confidence,
                reason=f"Strong negative momentum ({current_momentum:.2f}%), RSI: {current_rsi:.1f}",
                indicators=indicators
            )
        # RSI overbought - potential reversal, reduce/exit long
        elif current_rsi > rsi_overbought and current_position == Action.LONG:
            signal = Signal(
                action=Action.FLAT,
                confidence=0.7,
                reason=f"RSI overbought ({current_rsi:.1f}), exiting long",
                indicators=indicators
            )
        # RSI oversold - potential reversal, reduce/exit short
        elif current_rsi < rsi_oversold and current_position == Action.SHORT:
            signal = Signal(
                action=Action.FLAT,
                confidence=0.7,
                reason=f"RSI oversold ({current_rsi:.1f}), exiting short",
                indicators=indicators
            )
        # Weak or no momentum
        elif abs(current_momentum) < 1.0:
            signal = Signal(
                action=Action.FLAT,
                confidence=0.6,
                reason=f"Weak momentum ({current_momentum:.2f}%)",
                indicators=indicators
            )
        else:
            # Hold current position
            signal = Signal(
                action=current_position,
                confidence=0.4,
                reason="Moderate momentum, holding position",
                indicators=indicators
            )
        
        return self.apply_signal_filters(signal, indicators)
