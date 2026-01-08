import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.round import Round, RoundStatus
from app.models.agent import Agent
from app.models.agent_result import AgentResult
from app.schemas.agent import (
    AgentCreate, AgentUpdate, AgentResponse, AgentResultResponse
)
from app.utils.auth import get_current_user

router = APIRouter()


@router.post("/{round_id}/agents", response_model=AgentResponse)
def create_or_update_agent(
    round_id: uuid.UUID,
    data: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create or update an agent configuration for a round."""
    # Check round exists and is pending
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    if round_obj.status != RoundStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify agents after round has started"
        )
    
    # Check if agent already exists
    existing_agent = db.query(Agent).filter(
        Agent.user_id == current_user.id,
        Agent.round_id == round_id
    ).first()
    
    if existing_agent:
        # Update existing agent
        existing_agent.strategy_type = data.strategy_type
        existing_agent.config = data.config.model_dump()
        db.commit()
        db.refresh(existing_agent)
        agent = existing_agent
    else:
        # Create new agent
        agent = Agent(
            id=uuid.uuid4(),
            user_id=current_user.id,
            round_id=round_id,
            strategy_type=data.strategy_type,
            config=data.config.model_dump()
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
    
    return AgentResponse(
        id=agent.id,
        user_id=agent.user_id,
        round_id=agent.round_id,
        strategy_type=agent.strategy_type,
        config=agent.config,
        created_at=agent.created_at,
        result=None,
        user_nickname=current_user.nickname,
        user_color=current_user.color
    )


@router.get("/{round_id}/agents/me", response_model=AgentResponse)
def get_my_agent(
    round_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's agent in a round."""
    agent = db.query(Agent).filter(
        Agent.user_id == current_user.id,
        Agent.round_id == round_id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have an agent in this round"
        )
    
    result = None
    if agent.result:
        result = AgentResultResponse.model_validate(agent.result)
    
    return AgentResponse(
        id=agent.id,
        user_id=agent.user_id,
        round_id=agent.round_id,
        strategy_type=agent.strategy_type,
        config=agent.config,
        created_at=agent.created_at,
        result=result,
        user_nickname=current_user.nickname,
        user_color=current_user.color
    )


@router.get("/{round_id}/agents", response_model=list[AgentResponse])
def list_agents_in_round(
    round_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """List all agents in a round."""
    # Verify round exists
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    agents = db.query(Agent).filter(Agent.round_id == round_id).all()
    
    response = []
    for agent in agents:
        result = None
        if agent.result:
            result = AgentResultResponse.model_validate(agent.result)
        
        response.append(AgentResponse(
            id=agent.id,
            user_id=agent.user_id,
            round_id=agent.round_id,
            strategy_type=agent.strategy_type,
            config=agent.config,
            created_at=agent.created_at,
            result=result,
            user_nickname=agent.user.nickname if agent.user else None,
            user_color=agent.user.color if agent.user else None
        ))
    
    return response


@router.get("/{round_id}/agents/{agent_id}", response_model=AgentResponse)
def get_agent(
    round_id: uuid.UUID,
    agent_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get a specific agent's details."""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.round_id == round_id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    result = None
    if agent.result:
        result = AgentResultResponse.model_validate(agent.result)
    
    return AgentResponse(
        id=agent.id,
        user_id=agent.user_id,
        round_id=agent.round_id,
        strategy_type=agent.strategy_type,
        config=agent.config,
        created_at=agent.created_at,
        result=result,
        user_nickname=agent.user.nickname if agent.user else None,
        user_color=agent.user.color if agent.user else None
    )


@router.get("/{round_id}/agents/{agent_id}/results", response_model=AgentResultResponse)
def get_agent_results(
    round_id: uuid.UUID,
    agent_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get detailed results for an agent."""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.round_id == round_id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    
    if not agent.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results not available yet"
        )
    
    return AgentResultResponse.model_validate(agent.result)


@router.delete("/{round_id}/agents/me")
def delete_my_agent(
    round_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete the current user's agent from a round."""
    # Check round is pending
    round_obj = db.query(Round).filter(Round.id == round_id).first()
    if not round_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Round not found"
        )
    
    if round_obj.status != RoundStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete agents after round has started"
        )
    
    agent = db.query(Agent).filter(
        Agent.user_id == current_user.id,
        Agent.round_id == round_id
    ).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You don't have an agent in this round"
        )
    
    db.delete(agent)
    db.commit()
    
    return {"message": "Agent deleted successfully"}
