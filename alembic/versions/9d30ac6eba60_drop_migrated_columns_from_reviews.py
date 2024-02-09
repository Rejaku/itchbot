"""drop migrated columns from reviews

Revision ID: 9d30ac6eba60
Revises: bce3ebe19505
Create Date: 2024-02-09 13:14:57.012559

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d30ac6eba60'
down_revision = 'bce3ebe19505'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('reviews', 'game_name')
    op.drop_column('reviews', 'game_url')
    op.drop_column('reviews', 'user_name')


def downgrade() -> None:
    op.add_column('reviews', sa.Column('game_name', sa.String(200), nullable=False))
    op.add_column('reviews', sa.Column('game_url', sa.String(250), nullable=False))
    op.add_column('reviews', sa.Column('user_name', sa.String(100), nullable=False))
