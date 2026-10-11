"""create learner_concept_mastery table and link questions to concepts

Revision ID: b6c1d4e2f704
Revises: a5e1c8d2b903
Create Date: 2026-10-11 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6c1d4e2f704'
down_revision: Union[str, Sequence[str], None] = 'a5e1c8d2b903'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add concept_id to questions table
    with op.batch_alter_table('questions') as batch_op:
        batch_op.add_column(sa.Column('concept_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_questions_concept_id',
            'concepts',
            ['concept_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index(batch_op.f('ix_questions_concept_id'), ['concept_id'], unique=False)

    # 2. Add bkt_processed to assessment_attempts table
    with op.batch_alter_table('assessment_attempts') as batch_op:
        batch_op.add_column(
            sa.Column('bkt_processed', sa.Boolean(), nullable=False, server_default='0')
        )

    # 3. Create learner_concept_mastery table
    op.create_table(
        'learner_concept_mastery',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=100), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('concept_id', sa.String(length=36), nullable=False),
        sa.Column('mastery_probability', sa.Float(), nullable=False),
        sa.Column('observation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('p_l0', sa.Float(), nullable=False, server_default='0.1'),
        sa.Column('p_t', sa.Float(), nullable=False, server_default='0.1'),
        sa.Column('p_g', sa.Float(), nullable=False, server_default='0.2'),
        sa.Column('p_s', sa.Float(), nullable=False, server_default='0.1'),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['concept_id'], ['concepts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'concept_id', name='uq_student_concept_mastery')
    )
    op.create_index(op.f('ix_learner_concept_mastery_id'), 'learner_concept_mastery', ['id'], unique=False)
    op.create_index(op.f('ix_learner_concept_mastery_student_id'), 'learner_concept_mastery', ['student_id'], unique=False)
    op.create_index(op.f('ix_learner_concept_mastery_course_id'), 'learner_concept_mastery', ['course_id'], unique=False)
    op.create_index(op.f('ix_learner_concept_mastery_concept_id'), 'learner_concept_mastery', ['concept_id'], unique=False)
    op.create_index('ix_learner_concept_mastery_student_course', 'learner_concept_mastery', ['student_id', 'course_id'], unique=False)


def downgrade() -> None:
    # 3. Drop learner_concept_mastery table
    op.drop_index('ix_learner_concept_mastery_student_course', table_name='learner_concept_mastery')
    op.drop_index(op.f('ix_learner_concept_mastery_concept_id'), table_name='learner_concept_mastery')
    op.drop_index(op.f('ix_learner_concept_mastery_course_id'), table_name='learner_concept_mastery')
    op.drop_index(op.f('ix_learner_concept_mastery_student_id'), table_name='learner_concept_mastery')
    op.drop_index(op.f('ix_learner_concept_mastery_id'), table_name='learner_concept_mastery')
    op.drop_table('learner_concept_mastery')

    # 2. Drop bkt_processed from assessment_attempts
    with op.batch_alter_table('assessment_attempts') as batch_op:
        batch_op.drop_column('bkt_processed')

    # 1. Drop concept_id from questions
    with op.batch_alter_table('questions') as batch_op:
        batch_op.drop_index(batch_op.f('ix_questions_concept_id'))
        batch_op.drop_constraint('fk_questions_concept_id', type_='foreignkey')
        batch_op.drop_column('concept_id')

