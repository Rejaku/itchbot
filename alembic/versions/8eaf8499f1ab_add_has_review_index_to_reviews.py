"""add has_review index to reviews

Revision ID: 8eaf8499f1ab
Revises: 952fc691a7fc
Create Date: 2024-02-14 01:51:12.978510

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8eaf8499f1ab'
down_revision = '952fc691a7fc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('idx_reviews_hidden_has_review', 'reviews', ['hidden', 'has_review'])
    op.create_index('idx_reviews_reviewer_id_hidden_has_review', 'reviews', ['reviewer_id', 'hidden', 'has_review'])
    op.create_index('idx_reviews_game_id_hidden_has_review', 'reviews', ['game_id', 'hidden', 'has_review'])
    op.drop_index('idx_reviews_user_id', 'reviews')
    op.drop_index('idx_reviews_game_id', 'reviews')

def downgrade() -> None:
    op.drop_index('idx_reviews_hidden_has_review', 'reviews')
    op.drop_index('idx_reviews_user_id_hidden_has_review', 'reviews')
    op.drop_index('idx_reviews_game_id_hidden_has_review', 'reviews')
    op.create_index('idx_reviews_user_id', 'reviews', ['reviewer_id'])
    op.create_index('idx_reviews_game_id', 'reviews', ['game_id'])
