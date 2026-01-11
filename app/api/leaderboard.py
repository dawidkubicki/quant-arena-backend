import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, func
from app.database import get_db
from app.models.round import Round, RoundStatus
from app.models.agent import Agent, StrategyType
from app.models.agent_result import AgentResult
from app.models.user import User
from app.schemas.leaderboard import (
    LeaderboardEntry, 
    LeaderboardResponse,
    GlobalLeaderboardEntry,
    GlobalLeaderboardResponse
)

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
    ).order_by(desc(AgentResult.sharpe_ratio).nullslast()).all()
    
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


@router.get("/leaderboard/global", response_model=GlobalLeaderboardResponse)
def get_global_leaderboard(
    sort_by: str = Query(
        default="performance_score",
        description="Metric to sort by",
        enum=["performance_score", "avg_sharpe_ratio", "avg_total_return", "total_rounds", "win_rate", "avg_alpha"]
    ),
    limit: int = Query(default=100, ge=1, le=500, description="Number of users to return"),
    offset: int = Query(default=0, ge=0, description="Number of users to skip"),
    db: Session = Depends(get_db)
):
    """
    Get the global leaderboard aggregating user performance across all completed rounds.
    
    Performance score is calculated as a weighted combination of:
    - Average Sharpe ratio (40%)
    - Win rate (30%)
    - Average alpha (20%)
    - Total rounds participated (10%)
    """
    # Get all completed rounds
    completed_rounds = db.query(Round).filter(Round.status == RoundStatus.COMPLETED).all()
    
    if not completed_rounds:
        return GlobalLeaderboardResponse(
            entries=[],
            total_users=0,
            total_rounds_analyzed=0
        )
    
    completed_round_ids = [r.id for r in completed_rounds]
    
    # Get all users who have participated in completed rounds
    users_with_results = db.query(User).join(Agent).join(AgentResult).filter(
        Agent.round_id.in_(completed_round_ids),
        Agent.strategy_type != StrategyType.GHOST  # Exclude ghost agents
    ).distinct().all()
    
    # Build leaderboard entries
    global_entries = []
    
    for user in users_with_results:
        # Get all agent results for this user in completed rounds
        user_results = db.query(AgentResult, Agent, Round).join(
            Agent, AgentResult.agent_id == Agent.id
        ).join(
            Round, Agent.round_id == Round.id
        ).filter(
            Agent.user_id == user.id,
            Round.status == RoundStatus.COMPLETED,
            Agent.strategy_type != StrategyType.GHOST
        ).all()
        
        if not user_results:
            continue
        
        # Calculate aggregate statistics
        sharpe_ratios = [r.AgentResult.sharpe_ratio for r in user_results if r.AgentResult.sharpe_ratio is not None]
        returns = [r.AgentResult.total_return for r in user_results]
        alphas = [r.AgentResult.alpha for r in user_results if r.AgentResult.alpha is not None]
        
        total_rounds = len(user_results)
        avg_sharpe = sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else None
        best_sharpe = max(sharpe_ratios) if sharpe_ratios else None
        avg_return = sum(returns) / len(returns) if returns else 0.0
        best_return = max(returns) if returns else 0.0
        avg_alpha = sum(alphas) / len(alphas) if alphas else None
        best_alpha = max(alphas) if alphas else None
        
        # Calculate win statistics
        # For each round, get the ranking
        first_place = 0
        top_3 = 0
        top_10 = 0
        
        for result, agent, round_obj in user_results:
            # Get all results for this round, sorted by sharpe ratio
            round_results = db.query(AgentResult).join(Agent).filter(
                Agent.round_id == round_obj.id,
                Agent.strategy_type != StrategyType.GHOST
            ).order_by(desc(AgentResult.sharpe_ratio).nullslast()).all()
            
            # Find user's rank in this round
            rank = None
            for idx, r in enumerate(round_results, 1):
                if r.id == result.id:
                    rank = idx
                    break
            
            if rank == 1:
                first_place += 1
                top_3 += 1
                top_10 += 1
            elif rank and rank <= 3:
                top_3 += 1
                top_10 += 1
            elif rank and rank <= 10:
                top_10 += 1
        
        win_rate = (top_3 / total_rounds * 100) if total_rounds > 0 else 0.0
        
        # Calculate performance score (weighted metric)
        # Normalize components to 0-100 scale
        sharpe_score = min(100, (avg_sharpe or 0) * 20) if avg_sharpe and avg_sharpe > 0 else 0  # Sharpe of 5 = 100 points
        win_rate_score = win_rate  # Already 0-100
        alpha_score = min(100, (avg_alpha or 0) * 10) if avg_alpha and avg_alpha > 0 else 0  # Alpha of 10% = 100 points
        participation_score = min(100, total_rounds * 10)  # 10 rounds = 100 points
        
        performance_score = (
            sharpe_score * 0.40 +
            win_rate_score * 0.30 +
            alpha_score * 0.20 +
            participation_score * 0.10
        )
        
        global_entries.append({
            'user_id': user.id,
            'nickname': user.nickname,
            'color': user.color,
            'icon': user.icon,
            'total_rounds': total_rounds,
            'avg_sharpe_ratio': avg_sharpe,
            'best_sharpe_ratio': best_sharpe,
            'avg_total_return': avg_return,
            'best_total_return': best_return,
            'avg_alpha': avg_alpha,
            'best_alpha': best_alpha,
            'first_place_count': first_place,
            'top_3_count': top_3,
            'top_10_count': top_10,
            'win_rate': win_rate,
            'performance_score': performance_score
        })
    
    # Sort entries
    def get_sort_key(entry):
        value = entry.get(sort_by)
        if value is None:
            return (1, 0)  # Put None values at the end
        return (0, value)
    
    global_entries.sort(key=get_sort_key, reverse=True)
    
    # Add ranks and apply pagination
    ranked_entries = []
    for rank, entry in enumerate(global_entries, 1):
        ranked_entries.append(GlobalLeaderboardEntry(
            rank=rank,
            **entry
        ))
    
    # Apply pagination
    paginated_entries = ranked_entries[offset:offset + limit]
    
    # Calculate summary stats
    sharpe_values = [e.avg_sharpe_ratio for e in ranked_entries if e.avg_sharpe_ratio is not None]
    return_values = [e.avg_total_return for e in ranked_entries]
    alpha_values = [e.avg_alpha for e in ranked_entries if e.avg_alpha is not None]
    participation_values = [e.total_rounds for e in ranked_entries]
    
    return GlobalLeaderboardResponse(
        entries=paginated_entries,
        total_users=len(ranked_entries),
        total_rounds_analyzed=len(completed_rounds),
        highest_avg_sharpe=max(sharpe_values) if sharpe_values else None,
        highest_avg_return=max(return_values) if return_values else None,
        highest_avg_alpha=max(alpha_values) if alpha_values else None,
        most_rounds_participated=max(participation_values) if participation_values else 0
    )


@router.get("/leaderboard/global/me")
def get_my_global_ranking(
    user_id: uuid.UUID = Query(..., description="User ID to get ranking for"),
    db: Session = Depends(get_db)
):
    """Get the current user's global ranking across all completed rounds."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get all completed rounds
    completed_rounds = db.query(Round).filter(Round.status == RoundStatus.COMPLETED).all()
    
    if not completed_rounds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed rounds found"
        )
    
    completed_round_ids = [r.id for r in completed_rounds]
    
    # Get user's results
    user_results = db.query(AgentResult, Agent, Round).join(
        Agent, AgentResult.agent_id == Agent.id
    ).join(
        Round, Agent.round_id == Round.id
    ).filter(
        Agent.user_id == user_id,
        Round.status == RoundStatus.COMPLETED,
        Agent.strategy_type != StrategyType.GHOST
    ).all()
    
    if not user_results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed rounds found for this user"
        )
    
    # Calculate user's statistics (same logic as above)
    sharpe_ratios = [r.AgentResult.sharpe_ratio for r in user_results if r.AgentResult.sharpe_ratio is not None]
    returns = [r.AgentResult.total_return for r in user_results]
    alphas = [r.AgentResult.alpha for r in user_results if r.AgentResult.alpha is not None]
    
    total_rounds = len(user_results)
    avg_sharpe = sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else None
    avg_return = sum(returns) / len(returns) if returns else 0.0
    avg_alpha = sum(alphas) / len(alphas) if alphas else None
    
    # Calculate win statistics
    first_place = 0
    top_3 = 0
    top_10 = 0
    
    for result, agent, round_obj in user_results:
        round_results = db.query(AgentResult).join(Agent).filter(
            Agent.round_id == round_obj.id,
            Agent.strategy_type != StrategyType.GHOST
        ).order_by(desc(AgentResult.sharpe_ratio).nullslast()).all()
        
        rank = None
        for idx, r in enumerate(round_results, 1):
            if r.id == result.id:
                rank = idx
                break
        
        if rank == 1:
            first_place += 1
            top_3 += 1
            top_10 += 1
        elif rank and rank <= 3:
            top_3 += 1
            top_10 += 1
        elif rank and rank <= 10:
            top_10 += 1
    
    win_rate = (top_3 / total_rounds * 100) if total_rounds > 0 else 0.0
    
    # Calculate performance score
    sharpe_score = min(100, (avg_sharpe or 0) * 20) if avg_sharpe and avg_sharpe > 0 else 0
    win_rate_score = win_rate
    alpha_score = min(100, (avg_alpha or 0) * 10) if avg_alpha and avg_alpha > 0 else 0
    participation_score = min(100, total_rounds * 10)
    
    user_performance_score = (
        sharpe_score * 0.40 +
        win_rate_score * 0.30 +
        alpha_score * 0.20 +
        participation_score * 0.10
    )
    
    # Get all users' performance scores to determine rank
    # This is a simplified version - in production you might want to cache this
    all_users = db.query(User).join(Agent).join(AgentResult).filter(
        Agent.round_id.in_(completed_round_ids),
        Agent.strategy_type != StrategyType.GHOST
    ).distinct().all()
    
    user_scores = []
    for u in all_users:
        u_results = db.query(AgentResult).join(Agent).filter(
            Agent.user_id == u.id,
            Agent.round_id.in_(completed_round_ids),
            Agent.strategy_type != StrategyType.GHOST
        ).all()
        
        if not u_results:
            continue
        
        u_sharpes = [r.sharpe_ratio for r in u_results if r.sharpe_ratio is not None]
        u_returns = [r.total_return for r in u_results]
        u_alphas = [r.alpha for r in u_results if r.alpha is not None]
        
        u_total = len(u_results)
        u_avg_sharpe = sum(u_sharpes) / len(u_sharpes) if u_sharpes else None
        u_avg_alpha = sum(u_alphas) / len(u_alphas) if u_alphas else None
        
        # Calculate win stats for this user
        u_top_3 = 0
        for u_result in u_results:
            round_id = db.query(Agent.round_id).filter(Agent.id == u_result.agent_id).scalar()
            round_results = db.query(AgentResult).join(Agent).filter(
                Agent.round_id == round_id,
                Agent.strategy_type != StrategyType.GHOST
            ).order_by(desc(AgentResult.sharpe_ratio).nullslast()).all()
            
            for idx, r in enumerate(round_results, 1):
                if r.id == u_result.id and idx <= 3:
                    u_top_3 += 1
                    break
        
        u_win_rate = (u_top_3 / u_total * 100) if u_total > 0 else 0.0
        
        u_sharpe_score = min(100, (u_avg_sharpe or 0) * 20) if u_avg_sharpe and u_avg_sharpe > 0 else 0
        u_alpha_score = min(100, (u_avg_alpha or 0) * 10) if u_avg_alpha and u_avg_alpha > 0 else 0
        u_participation_score = min(100, u_total * 10)
        
        u_performance_score = (
            u_sharpe_score * 0.40 +
            u_win_rate * 0.30 +
            u_alpha_score * 0.20 +
            u_participation_score * 0.10
        )
        
        user_scores.append((u.id, u_performance_score))
    
    # Sort by performance score
    user_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Find user's rank
    user_rank = None
    for idx, (uid, score) in enumerate(user_scores, 1):
        if uid == user_id:
            user_rank = idx
            break
    
    return {
        'rank': user_rank,
        'total_users': len(user_scores),
        'total_rounds': total_rounds,
        'avg_sharpe_ratio': avg_sharpe,
        'avg_total_return': avg_return,
        'avg_alpha': avg_alpha,
        'win_rate': win_rate,
        'first_place_count': first_place,
        'top_3_count': top_3,
        'top_10_count': top_10,
        'performance_score': user_performance_score,
        'percentile': (1 - (user_rank - 1) / len(user_scores)) * 100 if user_rank and user_scores else 0
    }
