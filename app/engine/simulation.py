import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.round import Round
from app.models.agent import Agent, StrategyType
from app.models.agent_result import AgentResult
from app.engine.market import MarketEngine
from app.engine.execution import ExecutionEngine
from app.engine.strategies.base import Action
from app.engine.strategies.mean_reversion import MeanReversionStrategy
from app.engine.strategies.trend_following import TrendFollowingStrategy
from app.engine.strategies.momentum import MomentumStrategy
from app.engine.metrics import calculate_all_metrics


def get_strategy(strategy_type: StrategyType, config: Dict[str, Any]):
    """Factory function to create strategy instances."""
    strategies = {
        StrategyType.MEAN_REVERSION: MeanReversionStrategy,
        StrategyType.TREND_FOLLOWING: TrendFollowingStrategy,
        StrategyType.MOMENTUM: MomentumStrategy,
        StrategyType.GHOST: TrendFollowingStrategy,  # Ghost uses simple trend following
    }
    
    strategy_class = strategies.get(strategy_type)
    if not strategy_class:
        raise ValueError(f"Unknown strategy type: {strategy_type}")
    
    return strategy_class(config)


class AgentRunner:
    """Runs a single agent through the simulation."""
    
    def __init__(
        self,
        agent: Agent,
        initial_equity: float,
        base_slippage: float,
        fee_rate: float
    ):
        self.agent = agent
        self.strategy = get_strategy(agent.strategy_type, agent.config)
        self.execution = ExecutionEngine(initial_equity, base_slippage, fee_rate)
        self.risk_params = agent.config.get('risk_params', {})
        self.current_position = Action.FLAT
        self.survival_time = 0
    
    def process_tick(
        self,
        tick: int,
        prices: List[float],
        volatility: float
    ):
        """Process a single tick for this agent."""
        if self.execution.state.is_killed:
            return
        
        current_price = prices[-1]
        
        # Generate signal
        signal = self.strategy.generate_signal(prices, self.current_position)
        
        # Calculate position size
        position_size = self.strategy.get_position_size(
            self.execution.state.equity,
            current_price
        )
        
        # Execute trade if needed
        if signal.action != self.current_position and signal.confidence > 0.3:
            self.execution.execute_trade(
                tick=tick,
                target_action=signal.action,
                price=current_price,
                position_size=position_size,
                volatility=volatility,
                reason=signal.reason,
                risk_params=self.risk_params
            )
            self.current_position = signal.action
        
        # Update equity
        self.execution.update_equity(current_price)
        
        # Check risk limits
        self.execution.check_risk_limits(tick, current_price, self.risk_params, volatility)
        
        if not self.execution.state.is_killed:
            self.survival_time = tick + 1
    
    def get_results(self) -> Dict[str, Any]:
        """Get final results for this agent."""
        exec_results = self.execution.get_results()
        
        metrics = calculate_all_metrics(
            equity_curve=exec_results['equity_curve'],
            trades=exec_results['trades'],
            initial_equity=exec_results['initial_equity'],
            survival_time=self.survival_time
        )
        
        return {
            **metrics,
            'equity_curve': exec_results['equity_curve'],
            'trades': exec_results['trades'],
            'is_killed': exec_results['is_killed'],
            'kill_reason': exec_results['kill_reason']
        }


def run_simulation(db: Session, round_obj: Round, agents: List[Agent]):
    """
    Run the complete simulation for a round.
    
    Args:
        db: Database session
        round_obj: Round model instance
        agents: List of Agent model instances
    """
    # Extract market config
    market_config = round_obj.config.get('market', {})
    
    # Create market engine
    market = MarketEngine(
        seed=round_obj.market_seed,
        initial_price=market_config.get('initial_price', 100.0),
        base_volatility=market_config.get('base_volatility', 0.02),
        base_drift=market_config.get('base_drift', 0.0001),
        trend_probability=market_config.get('trend_probability', 0.3),
        volatile_probability=market_config.get('volatile_probability', 0.2),
        regime_persistence=market_config.get('regime_persistence', 0.95)
    )
    
    # Generate price series
    num_ticks = market_config.get('num_ticks', 1000)
    prices, market_states = market.generate_prices(num_ticks)
    
    # Store price data in round
    round_obj.price_data = prices
    
    # Initialize agent runners
    initial_equity = market_config.get('initial_equity', 100000.0)
    base_slippage = market_config.get('base_slippage', 0.001)
    fee_rate = market_config.get('fee_rate', 0.001)
    
    runners = [
        AgentRunner(agent, initial_equity, base_slippage, fee_rate)
        for agent in agents
    ]
    
    # Run simulation tick by tick
    for tick in range(num_ticks):
        # Get price history up to this tick
        price_history = prices[:tick + 1]
        current_volatility = market_states[tick].volatility if tick < len(market_states) else 0.02
        
        # Process each agent
        for runner in runners:
            runner.process_tick(tick, price_history, current_volatility)
    
    # Save results for each agent
    for runner, agent in zip(runners, agents):
        results = runner.get_results()
        
        # Create or update agent result
        agent_result = db.query(AgentResult).filter(
            AgentResult.agent_id == agent.id
        ).first()
        
        if agent_result:
            # Update existing result
            agent_result.final_equity = results['final_equity']
            agent_result.total_return = results['total_return']
            agent_result.sharpe_ratio = results['sharpe_ratio']
            agent_result.max_drawdown = results['max_drawdown']
            agent_result.calmar_ratio = results['calmar_ratio']
            agent_result.total_trades = results['total_trades']
            agent_result.win_rate = results['win_rate']
            agent_result.survival_time = results['survival_time']
            agent_result.equity_curve = results['equity_curve']
            agent_result.trades = results['trades']
        else:
            # Create new result
            agent_result = AgentResult(
                id=uuid.uuid4(),
                agent_id=agent.id,
                final_equity=results['final_equity'],
                total_return=results['total_return'],
                sharpe_ratio=results['sharpe_ratio'],
                max_drawdown=results['max_drawdown'],
                calmar_ratio=results['calmar_ratio'],
                total_trades=results['total_trades'],
                win_rate=results['win_rate'],
                survival_time=results['survival_time'],
                equity_curve=results['equity_curve'],
                trades=results['trades']
            )
            db.add(agent_result)
    
    db.commit()
