"""Add character base fields to TranslationJob

Revision ID: 1a2b3c4d5e6f
Revises: b2e468b624fb
Create Date: 2025-09-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = 'b2e468b624fb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('translation_jobs', sa.Column('character_profile', sa.JSON(), nullable=True))
    op.add_column('translation_jobs', sa.Column('character_base_images', sa.JSON(), nullable=True))
    op.add_column('translation_jobs', sa.Column('character_base_selected_index', sa.Integer(), nullable=True))
    op.add_column('translation_jobs', sa.Column('character_base_directory', sa.String(), nullable=True))


def downgrade():
    op.drop_column('translation_jobs', 'character_base_directory')
    op.drop_column('translation_jobs', 'character_base_selected_index')
    op.drop_column('translation_jobs', 'character_base_images')
    op.drop_column('translation_jobs', 'character_profile')

