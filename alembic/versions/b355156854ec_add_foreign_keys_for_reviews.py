"""add foreign keys for reviews

Revision ID: b355156854ec
Revises: 9d30ac6eba60
Create Date: 2024-02-09 22:57:48.949231

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b355156854ec'
down_revision = '9d30ac6eba60'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('reviews', 'game_id', existing_type=sa.String(50), type_=sa.Integer, existing_nullable=False, nullable=False)
    op.create_foreign_key('reviews_game_id_fkey', 'reviews', 'games', ['game_id'], ['game_id'])
    op.create_foreign_key('reviews_user_id_fkey', 'reviews', 'reviewers', ['user_id'], ['user_id'])


def downgrade() -> None:
    op.drop_constraint('reviews_user_id_fkey', 'reviews', type_='foreignkey')
    op.drop_constraint('reviews_game_id_fkey', 'reviews', type_='foreignkey')
    op.alter_column('reviews', 'game_id', existing_type=sa.Integer, type_=sa.String(50), existing_nullable=False, nullable=False)
