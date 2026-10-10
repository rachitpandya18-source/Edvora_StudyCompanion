"""create content_units table

Revision ID: e8c2f1a3b501
Revises: d7f92aabd290
Create Date: 2026-10-10 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8c2f1a3b501'
down_revision: Union[str, Sequence[str], None] = 'd7f92aabd290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'content_units',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('source_id', sa.String(length=36), nullable=False),
        sa.Column('unit_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('content_type', sa.String(length=50), nullable=False, server_default='text'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('char_start', sa.Integer(), nullable=True),
        sa.Column('char_end', sa.Integer(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('slide_number', sa.Integer(), nullable=True),
        sa.Column('timestamp_start', sa.Float(), nullable=True),
        sa.Column('timestamp_end', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('embedding', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_units_id'), 'content_units', ['id'], unique=False)
    op.create_index(op.f('ix_content_units_course_id'), 'content_units', ['course_id'], unique=False)
    op.create_index(op.f('ix_content_units_source_id'), 'content_units', ['source_id'], unique=False)
    op.create_index('ix_content_units_course_source', 'content_units', ['course_id', 'source_id'], unique=False)
    op.create_index('ix_content_units_source_unit_index', 'content_units', ['source_id', 'unit_index'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_content_units_source_unit_index', table_name='content_units')
    op.drop_index('ix_content_units_course_source', table_name='content_units')
    op.drop_index(op.f('ix_content_units_source_id'), table_name='content_units')
    op.drop_index(op.f('ix_content_units_course_id'), table_name='content_units')
    op.drop_index(op.f('ix_content_units_id'), table_name='content_units')
    op.drop_table('content_units')

