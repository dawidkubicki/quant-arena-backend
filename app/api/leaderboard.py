import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from app.database import get_db
from app.models.round import Round, RoundStatus
from app.models.agent import Agent, StrategyType
from app.models.agent_result import AgentResult
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse

router = APIRouter()


@router.get("/{round_id}/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(
    round_id: uuid.UUID,
    sort_by: str = Query(
        default="sharpe_ratio",
        description="Metric to sort by",
        enum=["sharpe_ratio", "total_return", "max_drawdown", "calmar_ratio", "win_rate", "survival_time", "alpha", "beta"]
    ),
    ascending: bool = Query(
        default=False,
        description="Sort ascending (only for max_drawdown, lower is better)"
    ),
    db: Session = Depends(get_db)
):
    """
    Get the leaderboard for a completed round.
    
    Supports sorting by multiple metrics:
    - sharpe_ratio (default, higher is better)
    - total_return (higher is better)
    - max_drawdown (lower is better)
    - calmar_ratio (higher is better)
    - win_rate (higher is better)
    - survival_time (higher is better)
    """
    # Get round
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    if round_obj.status != RoundStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Leaderboard only available for completed rounds"
        )
    
    # Get all agents with results
    agents_with_results = db.query(Agent, AgentResult).join(
        AgentResult, Agent.id == AgentResult.agent_id
    ).filter(Agent.round_id == round_id).all()
    
    if not agents_with_results:
        return LeaderboardResponse(
            round_id=round_id,
            round_name=round_obj.name,
            entries=[],
            total_participants=0
        )
    
    # Build entries
    entries = []
    for agent, result in agents_with_results:
        user = agent.user
        entries.append({
            'agent_id': agent.id,
            'user_id': agent.user_id,
            'nickname': user.nickname if user else "Unknown",
            'color': user.color if user else "#888888",
            'icon': user.icon if user else "user",
            'strategy_type': agent.strategy_type,
            'final_equity': result.final_equity,
            'total_return': result.total_return,
            'sharpe_ratio': result.sharpe_ratio,
            'max_drawdown': result.max_drawdown,
            'calmar_ratio': result.calmar_ratio,
            'win_rate': result.win_rate,
            'total_trades': result.total_trades,
            'survival_time': result.survival_time,
            # CAPM metrics
            'alpha': result.alpha,
            'beta': result.beta,
            'is_ghost': agent.strategy_type == StrategyType.GHOST
        })
    
    # Sort entries
    reverse = not ascending
    if sort_by == "max_drawdown":
        # For max_drawdown, lower is better, so reverse the sort direction
        reverse = ascending
    
    def get_sort_key(entry):
        value = entry.get(sort_by)
        if value is None:
            # Put None values at the end
            return (1, 0)
        return (0, value)
    
    entries.sort(key=get_sort_key, reverse=reverse)
    
    # Add ranks
    leaderboard_entries = []
    for rank, entry in enumerate(entries, 1):
        leaderboard_entries.append(LeaderboardEntry(
            rank=rank,
            **entry
        ))
    
    # Calculate summary stats
    sharpe_values = [e.sharpe_ratio for e in leaderboard_entries if e.sharpe_ratio is not None]
    return_values = [e.total_return for e in leaderboard_entries]
    dd_values = [e.max_drawdown for e in leaderboard_entries]
    survival_values = [e.survival_time for e in leaderboard_entries]
    
    return LeaderboardResponse(
        round_id=round_id,
        round_name=round_obj.name,
        entries=leaderboard_entries,
        total_participants=len(leaderboard_entries),
        best_sharpe=max(sharpe_values) if sharpe_values else None,
        best_return=max(return_values) if return_values else None,
        lowest_drawdown=min(dd_values) if dd_values else None,
        average_survival=sum(survival_values) / len(survival_values) if survival_values else None
    )


@router.get("/{round_id}/leaderboard/me")
def get_my_ranking(
    round_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get the current user's ranking in a round."""
    # Get round
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    if round_obj.status != RoundStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rankings only available for completed rounds"
        )
    
    # Get user's agent
    user_agent = db.query(Agent).filter(
        Agent.round_id == round_id,
        Agent.user_id == user_id
    ).first()
    
    if not user_agent or not user_agent.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No results found for this user in this round"
        )
    
    # Get all results sorted by Sharpe ratio
    all_results = db.query(AgentResult).join(Agent).filter(
        Agent.round_id == round_id
    ).order_by(desc(AgentResult.sharpe_ratio.nullslast())).all()
    
    # Find user's rank
    user_rank = None
    for idx, result in enumerate(all_results, 1):
        if result.agent_id == user_agent.id:
            user_rank = idx
            break
    
    user_result = user_agent.result
    
    return {
        'rank': user_rank,
        'total_participants': len(all_results),
        'final_equity': user_result.final_equity,
        'total_return': user_result.total_return,
        'sharpe_ratio': user_result.sharpe_ratio,
        'max_drawdown': user_result.max_drawdown,
        'percentile': (1 - (user_rank - 1) / len(all_results)) * 100 if all_results else 0
    }
