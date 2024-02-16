"""Add game_versions table

Revision ID: 7d0d2175e4f0
Revises: 8eaf8499f1ab
Create Date: 2024-02-16 18:29:07.119305

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d0d2175e4f0'
down_revision = '8eaf8499f1ab'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'game_versions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('version', sa.String(20)),
        sa.Column('devlog', sa.String(250)),
        sa.Column('platform_windows', sa.Integer, nullable=False, default=0),
        sa.Column('platform_linux', sa.Integer, nullable=False, default=0),
        sa.Column('platform_mac', sa.Integer, nullable=False, default=0),
        sa.Column('platform_android', sa.Integer, nullable=False, default=0),
        sa.Column('platform_web', sa.Integer(), nullable=False, default=0),
        sa.Column('stats_blocks', sa.Integer, nullable=False, default=0),
        sa.Column('stats_menus', sa.Integer, nullable=False, default=0),
        sa.Column('stats_options', sa.Integer, nullable=False, default=0),
        sa.Column('stats_words', sa.Integer, nullable=False, default=0),
        sa.Column('created_at', sa.FLOAT, nullable=False),
        sa.Column('released_at', sa.FLOAT, nullable=False)
    )


def downgrade():
    op.drop_table('game_versions')
