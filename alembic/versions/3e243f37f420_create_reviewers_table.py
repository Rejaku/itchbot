"""create reviewers table

Revision ID: 3e243f37f420
Revises: 9b07e1756a93
Create Date: 2024-02-07 10:44:21.783376

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3e243f37f420'
down_revision = '9b07e1756a93'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reviewers',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('created_at', sa.FLOAT, nullable=False),
        sa.Column('updated_at', sa.FLOAT, nullable=False),
        sa.Column('user_id', sa.Integer),
    )
    op.create_index('idx_reviewers_user_id', 'reviews', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_table('reviewers')
