"""create visual_novels table

Revision ID: 01f57399b444
Revises: 
Create Date: 2022-12-29 22:56:11.526727

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01f57399b444'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'visual_novels',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service', sa.String(50), nullable=False),
        sa.Column('game_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('description', sa.Unicode(200)),
        sa.Column('url', sa.String(250), nullable=False),
        sa.Column('thumb_url', sa.String(250)),
        sa.Column('latest_version', sa.String(20)),
        sa.Column('created_at', sa.FLOAT, nullable=False),
        sa.Column('updated_at', sa.FLOAT, nullable=False),
    )


def downgrade():
    op.drop_table('visual_novels')
