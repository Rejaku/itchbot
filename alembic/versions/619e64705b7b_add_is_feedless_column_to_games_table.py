"""add is_feedless column to games table

Revision ID: 619e64705b7b
Revises: 631656626735
Create Date: 2025-01-03 23:18:42.759203

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '619e64705b7b'
down_revision = '631656626735'
branch_labels = None
depends_on = None


def upgrade():
    # Add check_feed column with a default value of False
    op.add_column('games',
        sa.Column('is_feedless', sa.Boolean(), server_default='false', nullable=False)
    )


def downgrade():
    op.drop_column('games', 'is_feedless')
