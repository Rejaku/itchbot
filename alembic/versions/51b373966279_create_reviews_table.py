"""create reviews table

Revision ID: 51b373966279
Revises: 4c8c4496b7fb
Create Date: 2024-01-10 01:05:51.185202

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '51b373966279'
down_revision = '4c8c4496b7fb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'reviews',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('event_id', sa.Integer, nullable=False),
        sa.Column('created_at', sa.FLOAT, nullable=False),
        sa.Column('updated_at', sa.FLOAT, nullable=False),
        sa.Column('game_id', sa.Integer, nullable=False),
        sa.Column('user_name', sa.String(100), nullable=False),
        sa.Column('rating', sa.Integer, nullable=False),
        sa.Column('review', sa.Text)
    )


def downgrade() -> None:
    op.drop_table('reviews')
