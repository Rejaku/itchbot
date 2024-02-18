"""switch columns to boolean where appropriate

Revision ID: c4bc01260a22
Revises: 3c757877ba0b
Create Date: 2024-02-18 21:14:35.942108

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4bc01260a22'
down_revision = '3c757877ba0b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('games', 'platform_windows', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)
    op.alter_column('games', 'platform_linux', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)
    op.alter_column('games', 'platform_mac', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)
    op.alter_column('games', 'platform_android', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)
    op.alter_column('games', 'platform_web', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)
    op.alter_column('game_versions', 'platform_windows', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)
    op.alter_column('game_versions', 'platform_linux', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)
    op.alter_column('game_versions', 'platform_mac', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)
    op.alter_column('game_versions', 'platform_android', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)
    op.alter_column('game_versions', 'platform_web', existing_type=sa.Integer, type_=sa.Boolean, server_default=False)

def downgrade() -> None:
    op.alter_column('games', 'platform_windows', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
    op.alter_column('games', 'platform_linux', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
    op.alter_column('games', 'platform_mac', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
    op.alter_column('games', 'platform_android', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
    op.alter_column('games', 'platform_web', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
    op.alter_column('game_versions', 'platform_windows', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
    op.alter_column('game_versions', 'platform_linux', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
    op.alter_column('game_versions', 'platform_mac', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
    op.alter_column('game_versions', 'platform_android', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
    op.alter_column('game_versions', 'platform_web', existing_type=sa.Boolean, type_=sa.Integer, server_default=0)
