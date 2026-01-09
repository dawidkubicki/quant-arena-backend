import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.user import User
from app.models.round import Round, RoundStatus
from app.models.agent import Agent
from app.schemas.round import (
    RoundCreate, RoundResponse, RoundListResponse, RoundStatusResponse
)
from app.utils.auth import get_current_user, get_current_admin

router = APIRouter()


@router.post("/", response_model=RoundResponse)
def create_round(
    data: RoundCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new round (admin only)."""
    round_obj = Round(
        id=uuid.uuid4(),
        name=data.name,
        market_seed=data.market_seed,
        config=data.config.model_dump(),
        status=RoundStatus.PENDING
    )
    db.add(round_obj)
    db.commit()
    db.refresh(round_obj)
    
    return RoundResponse(
        id=round_obj.id,
        name=round_obj.name,
        status=round_obj.status,
        market_seed=round_obj.market_seed,
        config=round_obj.config,
        price_data=None,
        spy_returns=None,
        started_at=round_obj.started_at,
        completed_at=round_obj.completed_at,
        created_at=round_obj.created_at,
        agent_count=0
    )


@router.get("/", response_model=list[RoundListResponse])
def list_rounds(
    status_filter: Optional[RoundStatus] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List all rounds with agent counts."""
    query = db.query(
        Round,
        func.count(Agent.id).label('agent_count')
    ).outerjoin(Agent).group_by(Round.id)
    
    if status_filter:
        query = query.filter(Round.status == status_filter)
    
    results = query.order_by(Round.created_at.desc()).offset(skip).limit(limit).all()
    
    return [
        RoundListResponse(
            id=r.Round.id,
            name=r.Round.name,
            status=r.Round.status,
            market_seed=r.Round.market_seed,
            agent_count=r.agent_count,
            created_at=r.Round.created_at
        )
        for r in results
    ]


@router.get("/{round_id}", response_model=RoundResponse)
def get_round(
    round_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get round details including price data if completed."""
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    agent_count = db.query(Agent).filter(Agent.round_id == round_id).count()
    
    return RoundResponse(
        id=round_obj.id,
        name=round_obj.name,
        status=round_obj.status,
        market_seed=round_obj.market_seed,
        config=round_obj.config,
        price_data=round_obj.price_data,
        spy_returns=round_obj.spy_returns,
        started_at=round_obj.started_at,
        completed_at=round_obj.completed_at,
        created_at=round_obj.created_at,
        agent_count=agent_count
    )


@router.get("/{round_id}/status", response_model=RoundStatusResponse)
def get_round_status(
    round_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get round status (for polling)."""
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    return RoundStatusResponse(
        id=round_obj.id,
        status=round_obj.status,
        started_at=round_obj.started_at,
        completed_at=round_obj.completed_at
    )


@router.post("/{round_id}/start", response_model=RoundStatusResponse)
def start_round(
    round_id: uuid.UUID,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Start the simulation for a round (admin only)."""
    from app.engine.simulation import run_simulation
    from app.utils.ghost import add_ghost_agent_to_round
    
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    if round_obj.status != RoundStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Round is already {round_obj.status.value}"
        )
    
    # Add Ghost benchmark agent
    add_ghost_agent_to_round(db, round_id)
    
    # Get all agents including Ghost
    agents = db.query(Agent).filter(Agent.round_id == round_id).all()
    if len(agents) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No agents registered for this round"
        )
    
    # Update status to RUNNING
    round_obj.status = RoundStatus.RUNNING
    round_obj.started_at = datetime.utcnow()
    db.commit()
    
    try:
        # Run the simulation
        run_simulation(db, round_obj, agents)
        
        # Update status to COMPLETED
        round_obj.status = RoundStatus.COMPLETED
        round_obj.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        # Rollback status on error
        round_obj.status = RoundStatus.PENDING
        round_obj.started_at = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        )
    
    return RoundStatusResponse(
        id=round_obj.id,
        status=round_obj.status,
        started_at=round_obj.started_at,
        completed_at=round_obj.completed_at
    )


@router.post("/{round_id}/stop", response_model=RoundStatusResponse)
def force_stop_round(
    round_id: uuid.UUID,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Force stop a running round (admin only)."""
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    if round_obj.status != RoundStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Round is not running (current status: {round_obj.status.value})"
        )
    
    # Force stop the round by marking it as completed
    round_obj.status = RoundStatus.COMPLETED
    round_obj.completed_at = datetime.utcnow()
    db.commit()
    
    return RoundStatusResponse(
        id=round_obj.id,
        status=round_obj.status,
        started_at=round_obj.started_at,
        completed_at=round_obj.completed_at
    )


@router.delete("/{round_id}")
def delete_round(
    round_id: uuid.UUID,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a round (admin only)."""
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    if round_obj.status == RoundStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a running round"
        )
    
    db.delete(round_obj)
    db.commit()
    
    return {"message": "Round deleted successfully"}
