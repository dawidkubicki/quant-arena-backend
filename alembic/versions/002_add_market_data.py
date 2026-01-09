"""Add market data tables and alpha/beta columns

Revision ID: 002
Revises: 001
Create Date: 2025-01-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create market_datasets table
    op.execute("""
        CREATE TABLE market_datasets (
            id UUID PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            interval VARCHAR(10) NOT NULL,
            start_date TIMESTAMP NOT NULL,
            end_date TIMESTAMP NOT NULL,
            total_bars INTEGER NOT NULL DEFAULT 0,
            fetched_at TIMESTAMP DEFAULT NOW()
        );
        CREATE INDEX ix_market_datasets_symbol ON market_datasets(symbol);
    """)
    
    # Create market_data table for OHLCV bars
    op.execute("""
        CREATE TABLE market_data (
            id BIGSERIAL PRIMARY KEY,
            dataset_id UUID NOT NULL REFERENCES market_datasets(id) ON DELETE CASCADE,
            symbol VARCHAR(20) NOT NULL,
            datetime TIMESTAMP NOT NULL,
            open FLOAT NOT NULL,
            high FLOAT NOT NULL,
            low FLOAT NOT NULL,
            close FLOAT NOT NULL,
            volume BIGINT NOT NULL
        );
        CREATE INDEX ix_market_data_symbol ON market_data(symbol);
        CREATE INDEX ix_market_data_datetime ON market_data(datetime);
        CREATE INDEX ix_market_data_symbol_datetime ON market_data(symbol, datetime);
    """)
    
    # Add alpha/beta columns to agent_results
    op.execute("""
        ALTER TABLE agent_results 
        ADD COLUMN alpha FLOAT,
        ADD COLUMN beta FLOAT,
        ADD COLUMN cumulative_alpha JSONB DEFAULT '[]';
    """)
    
    # Add spy_returns to rounds for benchmark data
    op.execute("""
        ALTER TABLE rounds
        ADD COLUMN spy_returns JSONB;
    """)


def downgrade() -> None:
    # Remove spy_returns from rounds
    op.execute("""
        ALTER TABLE rounds DROP COLUMN IF EXISTS spy_returns;
    """)
    
    # Remove alpha/beta columns from agent_results
    op.execute("""
        ALTER TABLE agent_results 
        DROP COLUMN IF EXISTS alpha,
        DROP COLUMN IF EXISTS beta,
        DROP COLUMN IF EXISTS cumulative_alpha;
    """)
    
    # Drop market data tables
    op.execute("""
        DROP TABLE IF EXISTS market_data CASCADE;
        DROP TABLE IF EXISTS market_datasets CASCADE;
    """)
