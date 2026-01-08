import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class MarketRegime(Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"


@dataclass
class MarketState:
    """Current state of the market at a given tick."""
    tick: int
    price: float
    regime: MarketRegime
    volatility: float
    volume: float


class MarketEngine:
    """
    Generates realistic market price data using Geometric Brownian Motion
    with regime switching.
    """
    
    def __init__(
        self,
        seed: int,
        initial_price: float = 100.0,
        base_volatility: float = 0.02,
        base_drift: float = 0.0001,
        trend_probability: float = 0.3,
        volatile_probability: float = 0.2,
        regime_persistence: float = 0.95
    ):
        self.seed = seed
        self.initial_price = initial_price
        self.base_volatility = base_volatility
        self.base_drift = base_drift
        self.trend_probability = trend_probability
        self.volatile_probability = volatile_probability
        self.regime_persistence = regime_persistence
        
        self.rng = np.random.default_rng(seed)
        self.current_regime = MarketRegime.RANGE_BOUND
        
    def _determine_regime(self) -> MarketRegime:
        """Determine market regime with persistence."""
        # With high probability, stay in current regime
        if self.rng.random() < self.regime_persistence:
            return self.current_regime
        
        # Otherwise, transition to a new regime
        roll = self.rng.random()
        if roll < self.trend_probability / 2:
            return MarketRegime.TRENDING_UP
        elif roll < self.trend_probability:
            return MarketRegime.TRENDING_DOWN
        elif roll < self.trend_probability + self.volatile_probability:
            return MarketRegime.HIGH_VOLATILITY
        else:
            return MarketRegime.RANGE_BOUND
    
    def _get_regime_params(self, regime: MarketRegime) -> Tuple[float, float]:
        """Get drift and volatility multipliers for a regime."""
        if regime == MarketRegime.TRENDING_UP:
            return 3.0 * self.base_drift, 1.2 * self.base_volatility
        elif regime == MarketRegime.TRENDING_DOWN:
            return -2.0 * self.base_drift, 1.2 * self.base_volatility
        elif regime == MarketRegime.HIGH_VOLATILITY:
            return 0.0, 2.5 * self.base_volatility
        else:  # RANGE_BOUND
            return 0.0, self.base_volatility
    
    def generate_prices(self, num_ticks: int) -> Tuple[List[float], List[MarketState]]:
        """
        Generate price series using GBM with regime switching.
        
        Returns:
            prices: List of prices
            states: List of MarketState objects with full market info
        """
        prices = [self.initial_price]
        states = []
        
        dt = 1.0  # Time step (1 tick)
        
        for t in range(num_ticks):
            # Determine regime
            self.current_regime = self._determine_regime()
            drift, volatility = self._get_regime_params(self.current_regime)
            
            # Generate price change using GBM
            dW = self.rng.normal(0, 1)
            current_price = prices[-1]
            
            # GBM formula: dS = S * (mu * dt + sigma * sqrt(dt) * dW)
            dS = current_price * (drift * dt + volatility * np.sqrt(dt) * dW)
            new_price = max(current_price + dS, 0.01)  # Ensure price stays positive
            
            prices.append(new_price)
            
            # Generate volume (random with some regime dependency)
            base_volume = 1000000
            if self.current_regime == MarketRegime.HIGH_VOLATILITY:
                volume = base_volume * self.rng.uniform(1.5, 3.0)
            elif self.current_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                volume = base_volume * self.rng.uniform(1.2, 2.0)
            else:
                volume = base_volume * self.rng.uniform(0.8, 1.2)
            
            states.append(MarketState(
                tick=t,
                price=new_price,
                regime=self.current_regime,
                volatility=volatility,
                volume=volume
            ))
        
        return prices[1:], states  # Exclude initial price from output
    
    def get_current_volatility(self, prices: List[float], window: int = 20) -> float:
        """Calculate current realized volatility from recent prices."""
        if len(prices) < window:
            return self.base_volatility
        
        returns = np.diff(np.log(prices[-window:]))
        return np.std(returns) * np.sqrt(252)  # Annualized
