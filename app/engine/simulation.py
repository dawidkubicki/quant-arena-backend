"""
Simulation engine for running trading strategy rounds.

Uses real AAPL/SPY market data when available, falling back to
synthetic data generation for testing purposes.

Supports parallel agent processing using ThreadPoolExecutor for
handling 100+ participants efficiently.
"""

import uuid
import logging
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from app.models.round import Round, RoundStatus
from app.models.agent import Agent, StrategyType
from app.models.agent_result import AgentResult
from app.models.trade import Trade
from app.engine.market import MarketEngine
from app.engine.real_market import RealMarketEngine, check_market_data_available
from app.engine.execution import ExecutionEngine
from app.engine.strategies.base import Action
from app.engine.strategies.mean_reversion import MeanReversionStrategy
from app.engine.strategies.trend_following import TrendFollowingStrategy
from app.engine.strategies.momentum import MomentumStrategy
from app.engine.metrics import calculate_all_metrics

logger = logging.getLogger(__name__)


def _to_python_type(value):
    """
    Convert numpy types and datetime to native Python types for database compatibility.
    PostgreSQL JSONB cannot handle numpy types or datetime objects directly.
    """
    if value is None:
        return None
    elif isinstance(value, datetime):
        # Convert datetime to ISO string for JSON serialization
        return value.isoformat()
    elif isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32)):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, np.bool_):
        return bool(value)
    return value

# Configuration for parallel processing
MAX_WORKERS = 20  # Cap thread pool to avoid resource exhaustion
PROGRESS_UPDATE_INTERVAL = 10  # Update progress every N% of ticks


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
        volatility: float,
        timestamp: Optional[str] = None
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
            # Convert ISO string timestamp to datetime object if provided
            from datetime import datetime
            ts = datetime.fromisoformat(timestamp) if timestamp else None
            
            self.execution.execute_trade(
                tick=tick,
                target_action=signal.action,
                price=current_price,
                position_size=position_size,
                volatility=volatility,
                reason=signal.reason,
                risk_params=self.risk_params,
                timestamp=ts
            )
            self.current_position = signal.action
        
        # Update equity
        self.execution.update_equity(current_price)
        
        # Check risk limits
        from datetime import datetime
        ts = datetime.fromisoformat(timestamp) if timestamp else None
        self.execution.check_risk_limits(tick, current_price, self.risk_params, volatility, ts)
        
        if not self.execution.state.is_killed:
            self.survival_time = tick + 1
    
    def get_results(self, spy_returns: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Get final results for this agent.
        
        Args:
            spy_returns: SPY log returns for alpha/beta calculation
        """
        exec_results = self.execution.get_results()
        
        metrics = calculate_all_metrics(
            equity_curve=exec_results['equity_curve'],
            trades=exec_results['trades'],
            initial_equity=exec_results['initial_equity'],
            survival_time=self.survival_time,
            spy_returns=spy_returns
        )
        
        return {
            **metrics,
            'equity_curve': exec_results['equity_curve'],
            'trades': exec_results['trades'],
            'is_killed': exec_results['is_killed'],
            'kill_reason': exec_results['kill_reason']
        }


def _process_tick_parallel(
    runners: List[AgentRunner],
    tick: int,
    price_history: List[float],
    volatility: float,
    timestamp: Optional[str] = None
):
    """
    Process a single tick for all agents in parallel using ThreadPoolExecutor.
    
    Agents are independent during tick processing - they don't share state,
    so parallel execution is safe.
    
    Args:
        runners: List of agent runners
        tick: Current tick number
        price_history: Price history up to current tick
        volatility: Current market volatility
        timestamp: ISO timestamp for this tick (None for synthetic data)
    """
    num_workers = min(MAX_WORKERS, len(runners))
    
    if num_workers <= 1:
        # Sequential for single agent (avoid thread overhead)
        for runner in runners:
            runner.process_tick(tick, price_history, volatility, timestamp)
        return
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(runner.process_tick, tick, price_history, volatility, timestamp): runner
            for runner in runners
        }
        
        for future in as_completed(futures):
            # Propagate any exceptions from agent processing
            try:
                future.result()
            except Exception as e:
                runner = futures[future]
                logger.error(f"Error processing agent {runner.agent.id}: {e}")
                # Mark agent as killed if processing fails
                runner.execution.state.is_killed = True
                runner.execution.state.kill_reason = f"Processing error: {str(e)}"


def _update_round_progress(
    db: Session,
    round_id: uuid.UUID,
    progress: int,
    agents_processed: int = 0,
    total_agents: int = 0
):
    """Update round progress in the database."""
    db.execute(
        sa.text("""
            UPDATE rounds 
            SET progress = :progress, 
                agents_processed = :agents_processed,
                total_agents = :total_agents
            WHERE id = :round_id
        """),
        {
            "progress": progress,
            "agents_processed": agents_processed,
            "total_agents": total_agents,
            "round_id": str(round_id)
        }
    )
    db.commit()


# Import sqlalchemy text for raw SQL
import sqlalchemy as sa


def run_simulation_with_real_data(
    db: Session,
    round_obj: Round,
    agents: List[Agent]
):
    """
    Run simulation using real AAPL/SPY market data.
    
    This is the primary simulation mode that uses actual historical
    data for educationally accurate alpha/beta calculations.
    
    Uses parallel agent processing for efficient handling of many participants.
    """
    market_config = round_obj.config.get('market', {})
    
    # Initialize real market engine
    trading_interval = market_config.get('trading_interval', '5min')
    
    logger.info(f"Initializing RealMarketEngine with {trading_interval} interval")
    market = RealMarketEngine(db, trading_interval=trading_interval)
    
    # Get market summary
    summary = market.get_summary()
    logger.info(f"Market data loaded: {summary['num_ticks']} bars from {summary['start_date']} to {summary['end_date']}")
    
    # Determine number of ticks to simulate
    max_ticks = market_config.get('num_ticks')
    num_ticks = min(max_ticks, market.num_ticks) if max_ticks else market.num_ticks
    
    # Get price data and SPY returns
    prices = market.prices[:num_ticks]
    spy_returns = market.spy_returns[:num_ticks]
    
    # Get timestamps for each tick
    timestamps = [market.get_state(i).datetime.isoformat() for i in range(num_ticks)]
    
    # Store price data and SPY returns with timestamps for charting
    round_obj.price_data = [
        {"tick": i, "timestamp": timestamps[i], "value": float(prices[i])}
        for i in range(num_ticks)
    ]
    round_obj.spy_returns = [
        {"tick": i, "timestamp": timestamps[i], "value": float(spy_returns[i])}
        for i in range(num_ticks)
    ]
    round_obj.timestamps = timestamps
    
    # Initialize agent runners
    initial_equity = market_config.get('initial_equity', 100000.0)
    base_slippage = market_config.get('base_slippage', 0.001)
    fee_rate = market_config.get('fee_rate', 0.001)
    
    runners = [
        AgentRunner(agent, initial_equity, base_slippage, fee_rate)
        for agent in agents
    ]
    
    # Update round with total agents
    round_obj.total_agents = len(agents)
    db.commit()
    
    # Run simulation tick by tick with parallel agent processing
    logger.info(f"Running simulation for {num_ticks} ticks with {len(runners)} agents (parallel processing)")
    
    # Calculate progress update interval
    progress_interval = max(1, num_ticks // PROGRESS_UPDATE_INTERVAL)
    last_progress = 0
    
    for tick in range(num_ticks):
        # Get market state
        state = market.get_state(tick)
        price_history = prices[:tick + 1]
        timestamp = timestamps[tick] if tick < len(timestamps) else None
        
        # Process all agents in parallel
        _process_tick_parallel(runners, tick, price_history, state.volatility, timestamp)
        
        # Update progress periodically
        current_progress = int((tick + 1) / num_ticks * 100)
        if current_progress >= last_progress + PROGRESS_UPDATE_INTERVAL or tick == num_ticks - 1:
            _update_round_progress(db, round_obj.id, current_progress, 0, len(agents))
            last_progress = current_progress
            logger.debug(f"Simulation progress: {current_progress}% ({tick + 1}/{num_ticks} ticks)")
    
    # Save results for each agent with timestamps
    _save_agent_results(db, runners, agents, spy_returns, round_obj.id, timestamps)
    
    logger.info("Simulation completed successfully")


def run_simulation_with_synthetic_data(
    db: Session,
    round_obj: Round,
    agents: List[Agent]
):
    """
    Run simulation using synthetic GBM-generated data.
    
    This is the fallback mode when real market data is not available.
    Note: Alpha/beta calculations will be None in this mode.
    
    Uses parallel agent processing for efficient handling of many participants.
    """
    market_config = round_obj.config.get('market', {})
    
    logger.info("Using synthetic market data (real data not available)")
    
    # Create synthetic market engine
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
    
    # Store price data with ticks for charting (no timestamps for synthetic data)
    round_obj.price_data = [
        {"tick": i, "timestamp": None, "value": float(prices[i])}
        for i in range(num_ticks)
    ]
    round_obj.spy_returns = None  # No SPY data for synthetic mode
    round_obj.timestamps = None  # No timestamps for synthetic data
    
    # Initialize agent runners
    initial_equity = market_config.get('initial_equity', 100000.0)
    base_slippage = market_config.get('base_slippage', 0.001)
    fee_rate = market_config.get('fee_rate', 0.001)
    
    runners = [
        AgentRunner(agent, initial_equity, base_slippage, fee_rate)
        for agent in agents
    ]
    
    # Update round with total agents
    round_obj.total_agents = len(agents)
    db.commit()
    
    # Calculate progress update interval
    progress_interval = max(1, num_ticks // PROGRESS_UPDATE_INTERVAL)
    last_progress = 0
    
    # Run simulation tick by tick with parallel agent processing
    logger.info(f"Running simulation for {num_ticks} ticks with {len(runners)} agents (parallel processing)")
    
    for tick in range(num_ticks):
        price_history = prices[:tick + 1]
        current_volatility = market_states[tick].volatility if tick < len(market_states) else 0.02
        
        # Process all agents in parallel (no timestamps for synthetic data)
        _process_tick_parallel(runners, tick, price_history, current_volatility, None)
        
        # Update progress periodically
        current_progress = int((tick + 1) / num_ticks * 100)
        if current_progress >= last_progress + PROGRESS_UPDATE_INTERVAL or tick == num_ticks - 1:
            _update_round_progress(db, round_obj.id, current_progress, 0, len(agents))
            last_progress = current_progress
            logger.debug(f"Simulation progress: {current_progress}% ({tick + 1}/{num_ticks} ticks)")
    
    # Save results (no SPY returns or timestamps for synthetic data)
    _save_agent_results(db, runners, agents, spy_returns=None, round_id=round_obj.id, timestamps=None)


def _save_agent_results(
    db: Session,
    runners: List[AgentRunner],
    agents: List[Agent],
    spy_returns: Optional[List[float]],
    round_id: Optional[uuid.UUID] = None,
    timestamps: Optional[List[str]] = None
):
    """
    Save simulation results for all agents to the database.
    
    Updates agents_processed count as each agent's results are saved.
    
    Args:
        db: Database session
        runners: List of agent runners with results
        agents: List of agent models
        spy_returns: SPY returns for alpha/beta calculation
        round_id: Round ID for progress tracking
        timestamps: ISO timestamps for each tick (None for synthetic data)
    """
    total_agents = len(agents)
    
    for idx, (runner, agent) in enumerate(zip(runners, agents)):
        results = runner.get_results(spy_returns=spy_returns)
        
        # Create or update agent result
        agent_result = db.query(AgentResult).filter(
            AgentResult.agent_id == agent.id
        ).first()
        
        # Convert numpy types to native Python types for PostgreSQL compatibility
        final_equity = _to_python_type(results['final_equity'])
        total_return = _to_python_type(results['total_return'])
        sharpe_ratio = _to_python_type(results['sharpe_ratio'])
        max_drawdown = _to_python_type(results['max_drawdown'])
        calmar_ratio = _to_python_type(results['calmar_ratio'])
        total_trades = _to_python_type(results['total_trades'])
        win_rate = _to_python_type(results['win_rate'])
        survival_time = _to_python_type(results['survival_time'])
        alpha = _to_python_type(results.get('alpha'))
        beta = _to_python_type(results.get('beta'))
        
        # Convert equity curve and cumulative alpha to chart data format
        equity_curve_values = results['equity_curve']
        cumulative_alpha_values = results.get('cumulative_alpha', [])
        
        # Format as chart data with tick/timestamp/value
        equity_curve = [
            {
                "tick": i,
                "timestamp": timestamps[i] if timestamps and i < len(timestamps) else None,
                "value": _to_python_type(equity_curve_values[i])
            }
            for i in range(len(equity_curve_values))
        ]
        
        cumulative_alpha = [
            {
                "tick": i,
                "timestamp": timestamps[i] if timestamps and i < len(timestamps) else None,
                "value": _to_python_type(cumulative_alpha_values[i])
            }
            for i in range(len(cumulative_alpha_values))
        ]
        
        # Convert trades list (for JSONB storage in agent_result)
        trades_json = [
            {k: _to_python_type(v) for k, v in trade.items()}
            for trade in results['trades']
        ]
        
        if agent_result:
            # Update existing result
            agent_result.final_equity = final_equity
            agent_result.total_return = total_return
            agent_result.sharpe_ratio = sharpe_ratio
            agent_result.max_drawdown = max_drawdown
            agent_result.calmar_ratio = calmar_ratio
            agent_result.total_trades = total_trades
            agent_result.win_rate = win_rate
            agent_result.survival_time = survival_time
            agent_result.equity_curve = equity_curve
            agent_result.trades = trades_json
            # CAPM metrics
            agent_result.alpha = alpha
            agent_result.beta = beta
            agent_result.cumulative_alpha = cumulative_alpha
        else:
            # Create new result
            agent_result = AgentResult(
                id=uuid.uuid4(),
                agent_id=agent.id,
                final_equity=final_equity,
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                calmar_ratio=calmar_ratio,
                total_trades=total_trades,
                win_rate=win_rate,
                survival_time=survival_time,
                equity_curve=equity_curve,
                trades=trades_json,
                # CAPM metrics
                alpha=alpha,
                beta=beta,
                cumulative_alpha=cumulative_alpha
            )
            db.add(agent_result)
        
        # Delete old trade records for this agent (in case of re-simulation)
        db.query(Trade).filter(Trade.agent_id == agent.id).delete()
        
        # Save individual trades to the database
        # Convert numpy types to native Python types for PostgreSQL compatibility
        for trade_data in results['trades']:
            trade = Trade(
                id=uuid.uuid4(),
                agent_id=agent.id,
                tick=_to_python_type(trade_data['tick']),
                timestamp=trade_data.get('timestamp'),  # datetime object or None
                action=trade_data['action'],
                price=_to_python_type(trade_data['price']),
                executed_price=_to_python_type(trade_data['executed_price']),
                size=_to_python_type(trade_data['size']),
                cost=_to_python_type(trade_data['cost']),
                pnl=_to_python_type(trade_data['pnl']),
                equity_after=_to_python_type(trade_data['equity_after']),
                reason=trade_data['reason']
            )
            db.add(trade)
        
        # Update agents_processed count
        if round_id:
            agents_processed = idx + 1
            _update_round_progress(db, round_id, 100, agents_processed, total_agents)
    
    db.commit()


def run_simulation(db: Session, round_obj: Round, agents: List[Agent]):
    """
    Run the complete simulation for a round.
    
    Automatically uses real market data if available, otherwise
    falls back to synthetic data generation.
    
    Args:
        db: Database session
        round_obj: Round model instance
        agents: List of Agent model instances
    """
    # Check if real market data is available
    if check_market_data_available(db):
        run_simulation_with_real_data(db, round_obj, agents)
    else:
        logger.warning(
            "Real market data not available. "
            "Use POST /api/market-data/fetch to download AAPL and SPY data."
        )
        run_simulation_with_synthetic_data(db, round_obj, agents)
