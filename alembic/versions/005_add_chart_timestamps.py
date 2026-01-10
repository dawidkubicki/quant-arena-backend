"""add chart timestamps

Revision ID: 005
Revises: 004
Create Date: 2026-01-10 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add timestamp fields for chart data.
    
    Changes:
    1. Add timestamps column to rounds table (stores ISO timestamps for each tick)
    2. Add timestamp column to trades table (market timestamp for each trade)
    
    The price_data, spy_returns, equity_curve, and cumulative_alpha columns
    now store objects with {tick, timestamp, value} instead of just values.
    
    Note: Existing data will need to be reformatted when rounds are re-run.
    """
    # Add timestamps column to rounds
    op.add_column('rounds', sa.Column('timestamps', JSONB, nullable=True))
    
    # Add timestamp column to trades
    op.add_column('trades', sa.Column('timestamp', sa.DateTime, nullable=True))
    
    # No need to modify existing JSONB columns - they're flexible
    # Old data (arrays of floats) will be replaced when rounds are re-run
    # New data will be arrays of {tick, timestamp, value} objects


def downgrade():
    """Remove timestamp fields."""
    op.drop_column('rounds', 'timestamps')
    op.drop_column('trades', 'timestamp')
