"""create assessment tables (assessments, questions, assessment_attempts, attempt_answers)

Revision ID: a5e1c8d2b903
Revises: f9a3c2b1d402
Create Date: 2026-10-10 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5e1c8d2b903'
down_revision: Union[str, Sequence[str], None] = 'f9a3c2b1d402'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Assessments table
    op.create_table(
        'assessments',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('assessment_type', sa.String(length=50), nullable=False, server_default='mixed'),
        sa.Column('time_limit_minutes', sa.Integer(), nullable=True),
        sa.Column('total_marks', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessments_id'), 'assessments', ['id'], unique=False)
    op.create_index(op.f('ix_assessments_course_id'), 'assessments', ['course_id'], unique=False)

    # 2. Questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('assessment_id', sa.String(length=36), nullable=False),
        sa.Column('question_type', sa.String(length=32), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('marks', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('options_json', sa.JSON(), nullable=True),
        sa.Column('correct_answer', sa.Text(), nullable=False),
        sa.Column('tolerance', sa.Float(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_id'), 'questions', ['id'], unique=False)
    op.create_index(op.f('ix_questions_assessment_id'), 'questions', ['assessment_id'], unique=False)
    op.create_index('ix_questions_assessment_order', 'questions', ['assessment_id', 'order_index'], unique=False)

    # 3. Assessment Attempts table
    op.create_table(
        'assessment_attempts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('assessment_id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=100), nullable=False, server_default='default_student'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='in_progress'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('max_score', sa.Float(), nullable=True),
        sa.Column('percentage', sa.Float(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_assessment_attempts_id'), 'assessment_attempts', ['id'], unique=False)
    op.create_index(op.f('ix_assessment_attempts_assessment_id'), 'assessment_attempts', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_assessment_attempts_student_id'), 'assessment_attempts', ['student_id'], unique=False)

    # 4. Attempt Answers table
    op.create_table(
        'attempt_answers',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('attempt_id', sa.String(length=36), nullable=False),
        sa.Column('question_id', sa.String(length=36), nullable=False),
        sa.Column('student_answer', sa.Text(), nullable=True),
        sa.Column('is_correct', sa.Boolean(), nullable=True),
        sa.Column('marks_awarded', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['attempt_id'], ['assessment_attempts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('attempt_id', 'question_id', name='uq_attempt_question')
    )
    op.create_index(op.f('ix_attempt_answers_id'), 'attempt_answers', ['id'], unique=False)
    op.create_index(op.f('ix_attempt_answers_attempt_id'), 'attempt_answers', ['attempt_id'], unique=False)
    op.create_index(op.f('ix_attempt_answers_question_id'), 'attempt_answers', ['question_id'], unique=False)


def downgrade() -> None:
    # 4. Drop Attempt Answers
    op.drop_index(op.f('ix_attempt_answers_question_id'), table_name='attempt_answers')
    op.drop_index(op.f('ix_attempt_answers_attempt_id'), table_name='attempt_answers')
    op.drop_index(op.f('ix_attempt_answers_id'), table_name='attempt_answers')
    op.drop_table('attempt_answers')

    # 3. Drop Assessment Attempts
    op.drop_index(op.f('ix_assessment_attempts_student_id'), table_name='assessment_attempts')
    op.drop_index(op.f('ix_assessment_attempts_assessment_id'), table_name='assessment_attempts')
    op.drop_index(op.f('ix_assessment_attempts_id'), table_name='assessment_attempts')
    op.drop_table('assessment_attempts')

    # 2. Drop Questions
    op.drop_index('ix_questions_assessment_order', table_name='questions')
    op.drop_index(op.f('ix_questions_assessment_id'), table_name='questions')
    op.drop_index(op.f('ix_questions_id'), table_name='questions')
    op.drop_table('questions')

    # 1. Drop Assessments
    op.drop_index(op.f('ix_assessments_course_id'), table_name='assessments')
    op.drop_index(op.f('ix_assessments_id'), table_name='assessments')
    op.drop_table('assessments')

