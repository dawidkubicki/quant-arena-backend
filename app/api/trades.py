from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.trade import Trade
from app.models.agent import Agent
from app.schemas.trade import (
    TradeResponse, 
    TradeListResponse, 
    CompletedTradeResponse,
    CompletedTradesResponse
)

router = APIRouter(prefix="/trades", tags=["Trades"])


@router.get("/agent/{agent_id}", response_model=TradeListResponse)
def get_agent_trades(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get all trades for a specific agent (raw trade list).
    
    Returns trades in chronological order (by tick) along with summary statistics.
    For long-only strategies, you'll see OPEN_LONG and CLOSE_LONG actions.
    
    **For a clearer view of trade history with paired entry/exit, use:**
    `GET /trades/agent/{agent_id}/completed`
    
    **Returns:**
    - List of all trades with detailed information
    - Total number of trades
    - Total P&L across all trades
    - Number of winning and losing trades
    - Win rate percentage
    """
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get all trades for this agent, ordered by tick
    trades = db.query(Trade).filter(
        Trade.agent_id == agent_id
    ).order_by(Trade.tick.asc()).all()
    
    # Calculate statistics
    total_pnl = sum(trade.pnl for trade in trades)
    
    # Only count closing trades for win/loss statistics
    closing_trades = [t for t in trades if 'CLOSE' in t.action]
    winning_trades = len([t for t in closing_trades if t.pnl > 0])
    losing_trades = len([t for t in closing_trades if t.pnl < 0])
    total_closing = len(closing_trades)
    
    win_rate = (winning_trades / total_closing * 100) if total_closing > 0 else 0.0
    
    return TradeListResponse(
        trades=trades,
        total_trades=len(trades),
        total_pnl=total_pnl,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate
    )


@router.get("/agent/{agent_id}/completed", response_model=CompletedTradesResponse)
def get_agent_completed_trades(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get completed round-trip trades for an agent (entry + exit paired).
    
    This is the recommended endpoint for displaying trade history in the frontend.
    Each completed trade shows:
    - When you went long (entry)
    - When you sold (exit)
    - How long you held
    - P&L and return percentage
    
    **Long-only strategies:** Each trade is a buy→sell cycle.
    
    **Returns:**
    - List of completed trades with entry/exit details
    - Whether there's currently an open position
    - Summary statistics (win rate, average return, etc.)
    """
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get all trades for this agent, ordered by tick
    trades = db.query(Trade).filter(
        Trade.agent_id == agent_id
    ).order_by(Trade.tick.asc()).all()
    
    # Pair OPEN and CLOSE trades
    completed_trades = []
    open_position = None
    trade_number = 0
    
    for trade in trades:
        if trade.action == "OPEN_LONG":
            # Store as potential open position
            open_position = {
                "entry_tick": trade.tick,
                "entry_timestamp": trade.timestamp,
                "entry_price": trade.price,
                "entry_executed_price": trade.executed_price,
                "entry_reason": trade.reason,
                "size": trade.size,
                "entry_cost": trade.cost
            }
        elif trade.action == "CLOSE_LONG" and open_position:
            # Complete the trade pair
            trade_number += 1
            
            entry_price = open_position["entry_executed_price"]
            exit_price = trade.executed_price
            return_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0
            
            completed_trade = CompletedTradeResponse(
                trade_number=trade_number,
                entry_tick=open_position["entry_tick"],
                entry_timestamp=open_position["entry_timestamp"],
                entry_price=open_position["entry_price"],
                entry_executed_price=entry_price,
                entry_reason=open_position["entry_reason"],
                exit_tick=trade.tick,
                exit_timestamp=trade.timestamp,
                exit_price=trade.price,
                exit_executed_price=exit_price,
                exit_reason=trade.reason,
                size=trade.size,
                total_cost=open_position["entry_cost"] + trade.cost,
                pnl=trade.pnl,
                return_pct=return_pct,
                duration_ticks=trade.tick - open_position["entry_tick"],
                is_winner=trade.pnl > 0
            )
            completed_trades.append(completed_trade)
            open_position = None
    
    # Calculate statistics
    total_pnl = sum(t.pnl for t in completed_trades)
    winners = [t for t in completed_trades if t.is_winner]
    losers = [t for t in completed_trades if not t.is_winner]
    total_completed = len(completed_trades)
    
    win_rate = (len(winners) / total_completed * 100) if total_completed > 0 else 0.0
    avg_return = sum(t.return_pct for t in completed_trades) / total_completed if total_completed > 0 else 0.0
    avg_duration = sum(t.duration_ticks for t in completed_trades) / total_completed if total_completed > 0 else 0.0
    
    best_pnl = max((t.pnl for t in completed_trades), default=0.0)
    worst_pnl = min((t.pnl for t in completed_trades), default=0.0)
    
    return CompletedTradesResponse(
        completed_trades=completed_trades,
        has_open_position=open_position is not None,
        open_position=open_position,
        total_completed_trades=total_completed,
        total_pnl=total_pnl,
        winning_trades=len(winners),
        losing_trades=len(losers),
        win_rate=win_rate,
        avg_return_pct=avg_return,
        avg_duration_ticks=avg_duration,
        best_trade_pnl=best_pnl,
        worst_trade_pnl=worst_pnl
    )


@router.get("/agent/{agent_id}/summary")
def get_agent_trade_summary(
    agent_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a summary of trade statistics for a specific agent.
    
    This is a lightweight endpoint that returns only aggregated statistics
    without the full trade list (useful for dashboards).
    
    **Returns:**
    - Total number of trades
    - Total P&L
    - Win rate
    - Average winning trade P&L
    - Average losing trade P&L
    - Largest win and loss
    """
    # Verify agent exists
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Get all trades for statistics
    trades = db.query(Trade).filter(Trade.agent_id == agent_id).all()
    
    if not trades:
        return {
            "agent_id": agent_id,
            "total_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_winning_trade": 0.0,
            "avg_losing_trade": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0
        }
    
    # Calculate statistics
    total_pnl = sum(trade.pnl for trade in trades)
    
    # Only count closing trades
    closing_trades = [t for t in trades if 'CLOSE' in t.action]
    winning_trades = [t for t in closing_trades if t.pnl > 0]
    losing_trades = [t for t in closing_trades if t.pnl < 0]
    
    total_closing = len(closing_trades)
    win_rate = (len(winning_trades) / total_closing * 100) if total_closing > 0 else 0.0
    
    avg_winning = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
    avg_losing = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
    
    largest_win = max((t.pnl for t in winning_trades), default=0.0)
    largest_loss = min((t.pnl for t in losing_trades), default=0.0)
    
    return {
        "agent_id": agent_id,
        "total_trades": len(trades),
        "total_closing_trades": total_closing,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "avg_winning_trade": avg_winning,
        "avg_losing_trade": avg_losing,
        "largest_win": largest_win,
        "largest_loss": largest_loss,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades)
    }


@router.get("/round/{round_id}/all-trades")
def get_round_trades(
    round_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get trades for all agents in a specific round.
    
    Useful for comparing trading activity across all participants in a round.
    
    **Returns:**
    - Dictionary mapping agent_id to their trades
    - Aggregated statistics for the entire round
    """
    # Get all agents in this round
    agents = db.query(Agent).filter(Agent.round_id == round_id).all()
    
    if not agents:
        raise HTTPException(status_code=404, detail="Round not found or no agents in round")
    
    # Get trades for all agents in this round
    agent_ids = [agent.id for agent in agents]
    trades = db.query(Trade).filter(
        Trade.agent_id.in_(agent_ids)
    ).order_by(Trade.agent_id, Trade.tick).all()
    
    # Group trades by agent
    trades_by_agent = {}
    for agent in agents:
        agent_trades = [t for t in trades if t.agent_id == agent.id]
        trades_by_agent[str(agent.id)] = {
            "agent_id": agent.id,
            "user_id": agent.user_id,
            "strategy_type": agent.strategy_type.value,
            "trades": [TradeResponse.model_validate(t) for t in agent_trades],
            "trade_count": len(agent_trades)
        }
    
    return {
        "round_id": round_id,
        "total_agents": len(agents),
        "total_trades": len(trades),
        "trades_by_agent": trades_by_agent
    }
