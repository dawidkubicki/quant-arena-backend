"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create round_status enum
    round_status = postgresql.ENUM('PENDING', 'RUNNING', 'COMPLETED', name='roundstatus')
    round_status.create(op.get_bind(), checkfirst=True)
    
    # Create strategy_type enum
    strategy_type = postgresql.ENUM('MEAN_REVERSION', 'TREND_FOLLOWING', 'MOMENTUM', 'GHOST', name='strategytype')
    strategy_type.create(op.get_bind(), checkfirst=True)
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('supabase_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=True, index=True),
        sa.Column('nickname', sa.String(50), nullable=False, index=True),
        sa.Column('color', sa.String(7), nullable=False, default='#3B82F6'),
        sa.Column('icon', sa.String(50), nullable=False, default='user'),
        sa.Column('is_admin', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create rounds table
    op.create_table(
        'rounds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'RUNNING', 'COMPLETED', name='roundstatus'), nullable=False, default='PENDING'),
        sa.Column('market_seed', sa.Integer(), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False, default={}),
        sa.Column('price_data', postgresql.JSONB(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('round_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rounds.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_type', sa.Enum('MEAN_REVERSION', 'TREND_FOLLOWING', 'MOMENTUM', 'GHOST', name='strategytype'), nullable=False),
        sa.Column('config', postgresql.JSONB(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'round_id', name='unique_user_round'),
    )
    
    # Create agent_results table
    op.create_table(
        'agent_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('final_equity', sa.Float(), nullable=False),
        sa.Column('total_return', sa.Float(), nullable=False),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=False),
        sa.Column('calmar_ratio', sa.Float(), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=False, default=0),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('survival_time', sa.Integer(), nullable=False),
        sa.Column('equity_curve', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('trades', postgresql.JSONB(), nullable=False, default=[]),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('agent_results')
    op.drop_table('agents')
    op.drop_table('rounds')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS strategytype')
    op.execute('DROP TYPE IF EXISTS roundstatus')
