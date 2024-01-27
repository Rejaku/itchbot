"""Add error column to games table

Revision ID: 432c2bf7e774
Revises: 9b07e1756a93
Create Date: 2024-01-27 19:45:03.484281

"""
from alembic import op
from sqlalchemy import Column, Text

# revision identifiers, used by Alembic.
revision = '432c2bf7e774'
down_revision = '9b07e1756a93'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('games', Column('error', Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('games', 'error')
