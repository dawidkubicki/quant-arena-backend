"""Add trades table for trade history tracking

Revision ID: 003
Revises: 002
Create Date: 2026-01-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create trades table to store individual buy/sell transactions
    op.execute("""
        CREATE TABLE trades (
            id UUID PRIMARY KEY,
            agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            tick INTEGER NOT NULL,
            action VARCHAR(20) NOT NULL,
            price FLOAT NOT NULL,
            executed_price FLOAT NOT NULL,
            size FLOAT NOT NULL,
            cost FLOAT NOT NULL,
            pnl FLOAT NOT NULL DEFAULT 0.0,
            equity_after FLOAT NOT NULL,
            reason VARCHAR(200),
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        -- Indexes for efficient querying
        CREATE INDEX idx_trades_agent_id ON trades(agent_id);
        CREATE INDEX idx_trades_agent_tick ON trades(agent_id, tick);
    """)


def downgrade() -> None:
    # Drop trades table
    op.execute("""
        DROP TABLE IF EXISTS trades CASCADE;
    """)
