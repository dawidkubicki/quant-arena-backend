"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use raw SQL for cleaner enum and table creation
    op.execute("""
        CREATE TYPE roundstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED');
        CREATE TYPE strategytype AS ENUM ('MEAN_REVERSION', 'TREND_FOLLOWING', 'MOMENTUM', 'GHOST');
        
        CREATE TABLE users (
            id UUID PRIMARY KEY,
            supabase_id VARCHAR(255) NOT NULL UNIQUE,
            email VARCHAR(255),
            nickname VARCHAR(50) NOT NULL,
            color VARCHAR(7) NOT NULL DEFAULT '#3B82F6',
            icon VARCHAR(50) NOT NULL DEFAULT 'user',
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE INDEX ix_users_supabase_id ON users(supabase_id);
        CREATE INDEX ix_users_email ON users(email);
        CREATE INDEX ix_users_nickname ON users(nickname);
        
        CREATE TABLE rounds (
            id UUID PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            status roundstatus NOT NULL DEFAULT 'PENDING',
            market_seed INTEGER NOT NULL,
            config JSONB NOT NULL DEFAULT '{}',
            price_data JSONB,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE TABLE agents (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            round_id UUID NOT NULL REFERENCES rounds(id) ON DELETE CASCADE,
            strategy_type strategytype NOT NULL,
            config JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT unique_user_round UNIQUE (user_id, round_id)
        );
        
        CREATE TABLE agent_results (
            id UUID PRIMARY KEY,
            agent_id UUID NOT NULL UNIQUE REFERENCES agents(id) ON DELETE CASCADE,
            final_equity FLOAT NOT NULL,
            total_return FLOAT NOT NULL,
            sharpe_ratio FLOAT,
            max_drawdown FLOAT NOT NULL,
            calmar_ratio FLOAT,
            total_trades INTEGER NOT NULL DEFAULT 0,
            win_rate FLOAT,
            survival_time INTEGER NOT NULL,
            equity_curve JSONB NOT NULL DEFAULT '[]',
            trades JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS agent_results CASCADE;
        DROP TABLE IF EXISTS agents CASCADE;
        DROP TABLE IF EXISTS rounds CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TYPE IF EXISTS strategytype;
        DROP TYPE IF EXISTS roundstatus;
    """)
