"""add has_review column to reviews

Revision ID: 952fc691a7fc
Revises: 1c13100e117f
Create Date: 2024-02-14 01:37:11.172551

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '952fc691a7fc'
down_revision = '1c13100e117f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('reviews', sa.Column('has_review', sa.BOOLEAN, nullable=False, default=False))
    op.create_index('idx_reviews_hidden_has_review', 'games', ['hidden', 'has_review'])
    op.create_index('idx_reviews_user_id_hidden_has_review', 'games', ['user_id', 'hidden', 'has_review'])
    op.create_index('idx_reviews_game_id_hidden_has_review', 'games', ['game_id', 'hidden', 'has_review'])
    op.drop_index('idx_reviews_user_id')
    op.drop_index('idx_reviews_game_id')

def downgrade() -> None:
    op.drop_index('idx_reviews_hidden_has_review')
    op.drop_index('idx_reviews_user_id_hidden_has_review')
    op.drop_index('idx_reviews_game_id_hidden_has_review')
    op.drop_column('reviews', 'has_review')
    op.create_index('idx_reviews_user_id', 'reviews', ['user_id'])
    op.create_index('idx_reviews_game_id', 'reviews', ['game_id'])
