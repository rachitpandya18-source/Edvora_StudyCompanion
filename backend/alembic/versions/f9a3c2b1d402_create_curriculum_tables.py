"""create curriculum tables (topics, concepts, concept_prerequisites)

Revision ID: f9a3c2b1d402
Revises: e8c2f1a3b501
Create Date: 2026-10-10 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9a3c2b1d402'
down_revision: Union[str, Sequence[str], None] = 'e8c2f1a3b501'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Topics table
    op.create_table(
        'topics',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_topics_id'), 'topics', ['id'], unique=False)
    op.create_index(op.f('ix_topics_course_id'), 'topics', ['course_id'], unique=False)
    op.create_index('ix_topics_course_order', 'topics', ['course_id', 'order_index'], unique=False)

    # 2. Concepts table
    op.create_table(
        'concepts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('topic_id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_concepts_id'), 'concepts', ['id'], unique=False)
    op.create_index(op.f('ix_concepts_course_id'), 'concepts', ['course_id'], unique=False)
    op.create_index(op.f('ix_concepts_topic_id'), 'concepts', ['topic_id'], unique=False)
    op.create_index('ix_concepts_topic_order', 'concepts', ['topic_id', 'order_index'], unique=False)

    # 3. Concept Prerequisites table (directed relationship edge)
    op.create_table(
        'concept_prerequisites',
        sa.Column('concept_id', sa.String(length=36), nullable=False),
        sa.Column('prerequisite_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('concept_id != prerequisite_id', name='ck_concept_prerequisite_no_self'),
        sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prerequisite_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('concept_id', 'prerequisite_id')
    )
    op.create_index(op.f('ix_concept_prerequisites_concept_id'), 'concept_prerequisites', ['concept_id'], unique=False)
    op.create_index(op.f('ix_concept_prerequisites_prerequisite_id'), 'concept_prerequisites', ['prerequisite_id'], unique=False)


def downgrade() -> None:
    # 3. Drop Concept Prerequisites
    op.drop_index(op.f('ix_concept_prerequisites_prerequisite_id'), table_name='concept_prerequisites')
    op.drop_index(op.f('ix_concept_prerequisites_concept_id'), table_name='concept_prerequisites')
    op.drop_table('concept_prerequisites')

    # 2. Drop Concepts
    op.drop_index('ix_concepts_topic_order', table_name='concepts')
    op.drop_index(op.f('ix_concepts_topic_id'), table_name='concepts')
    op.drop_index(op.f('ix_concepts_course_id'), table_name='concepts')
    op.drop_index(op.f('ix_concepts_id'), table_name='concepts')
    op.drop_table('concepts')

    # 1. Drop Topics
    op.drop_index('ix_topics_course_order', table_name='topics')
    op.drop_index(op.f('ix_topics_course_id'), table_name='topics')
    op.drop_index(op.f('ix_topics_id'), table_name='topics')
    op.drop_table('topics')

