import uuid
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.agent import Agent, StrategyType


# Default Ghost agent configuration - simple trend following benchmark
GHOST_CONFIG = {
    "strategy_params": {
        "fast_window": 10,
        "slow_window": 30,
        "atr_multiplier": 2.0,
        "lookback_window": 20,
        "entry_threshold": 2.0,
        "exit_threshold": 0.5,
        "momentum_window": 14,
        "rsi_window": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30
    },
    "signal_stack": {
        "use_sma": True,
        "sma_window": 20,
        "use_rsi": False,
        "rsi_window": 14,
        "rsi_overbought": 70,
        "rsi_oversold": 30,
        "use_volatility_filter": False,
        "volatility_window": 20,
        "volatility_threshold": 1.5
    },
    "risk_params": {
        "position_size_pct": 10.0,
        "max_leverage": 1.0,
        "stop_loss_pct": 5.0,
        "take_profit_pct": 15.0,
        "max_drawdown_kill": 25.0
    }
}


def get_or_create_ghost_user(db: Session) -> User:
    """Get or create the Ghost benchmark user."""
    ghost_user = db.query(User).filter(User.supabase_id == "ghost").first()
    
    if not ghost_user:
        ghost_user = User(
            id=uuid.uuid4(),
            supabase_id="ghost",  # Special system ID
            email=None,
            nickname="Ghost",
            color="#6B7280",  # Gray
            icon="ghost",
            is_admin=False
        )
        db.add(ghost_user)
        db.commit()
        db.refresh(ghost_user)
    
    return ghost_user


def add_ghost_agent_to_round(db: Session, round_id: uuid.UUID) -> Agent:
    """
    Add a Ghost benchmark agent to a round.
    The Ghost agent uses a simple trend following strategy as a benchmark.
    """
    ghost_user = get_or_create_ghost_user(db)
    
    # Check if ghost agent already exists
    existing = db.query(Agent).filter(
        Agent.user_id == ghost_user.id,
        Agent.round_id == round_id
    ).first()
    
    if existing:
        return existing
    
    # Create ghost agent
    ghost_agent = Agent(
        id=uuid.uuid4(),
        user_id=ghost_user.id,
        round_id=round_id,
        strategy_type=StrategyType.GHOST,
        config=GHOST_CONFIG
    )
    
    db.add(ghost_agent)
    db.commit()
    db.refresh(ghost_agent)
    
    return ghost_agent
