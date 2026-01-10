"""Add progress tracking fields to rounds table

Revision ID: 004
Revises: 003
Create Date: 2026-01-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add FAILED status to the enum
    op.execute("ALTER TYPE roundstatus ADD VALUE IF NOT EXISTS 'FAILED'")
    
    # Add progress tracking columns
    op.add_column('rounds', sa.Column('progress', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('rounds', sa.Column('agents_processed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('rounds', sa.Column('total_agents', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('rounds', sa.Column('error_message', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove progress tracking columns
    op.drop_column('rounds', 'error_message')
    op.drop_column('rounds', 'total_agents')
    op.drop_column('rounds', 'agents_processed')
    op.drop_column('rounds', 'progress')
    
    # Note: PostgreSQL doesn't support removing enum values easily
    # The FAILED status will remain in the enum after downgrade
