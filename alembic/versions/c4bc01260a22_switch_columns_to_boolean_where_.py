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
    for table in ['games', 'game_versions']:
        for column in ['platform_windows', 'platform_linux', 'platform_mac', 'platform_android', 'platform_web']:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT')
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE bool USING CASE WHEN {column}=0 THEN FALSE ELSE TRUE END')
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT FALSE')

def downgrade() -> None:
    for table in ['games', 'game_versions']:
        for column in ['platform_windows', 'platform_linux', 'platform_mac', 'platform_android', 'platform_web']:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT')
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE integer USING CASE WHEN {column}=FALSE THEN 0 ELSE 1 END')
