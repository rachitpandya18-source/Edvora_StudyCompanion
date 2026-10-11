"""create tutor_threads and tutor_messages tables

Revision ID: c7d3e5f1a805
Revises: b6c1d4e2f704
Create Date: 2026-10-11 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d3e5f1a805'
down_revision: Union[str, Sequence[str], None] = 'b6c1d4e2f704'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tutor_threads table
    op.create_table(
        'tutor_threads',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('course_id', sa.String(length=36), nullable=False),
        sa.Column('student_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('tutor_threads') as batch_op:
        batch_op.create_index(batch_op.f('ix_tutor_threads_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_tutor_threads_course_id'), ['course_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_tutor_threads_student_id'), ['student_id'], unique=False)
        batch_op.create_index('ix_tutor_threads_course_student', ['course_id', 'student_id'], unique=False)

    # 2. Create tutor_messages table
    op.create_table(
        'tutor_messages',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('thread_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('citations_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['tutor_threads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('tutor_messages') as batch_op:
        batch_op.create_index(batch_op.f('ix_tutor_messages_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_tutor_messages_thread_id'), ['thread_id'], unique=False)
        batch_op.create_index('ix_tutor_messages_thread_created', ['thread_id', 'created_at'], unique=False)


def downgrade() -> None:
    # 1. Drop tutor_messages table
    with op.batch_alter_table('tutor_messages') as batch_op:
        batch_op.drop_index('ix_tutor_messages_thread_created')
        batch_op.drop_index(batch_op.f('ix_tutor_messages_thread_id'))
        batch_op.drop_index(batch_op.f('ix_tutor_messages_id'))
    op.drop_table('tutor_messages')

    # 2. Drop tutor_threads table
    with op.batch_alter_table('tutor_threads') as batch_op:
        batch_op.drop_index('ix_tutor_threads_course_student')
        batch_op.drop_index(batch_op.f('ix_tutor_threads_student_id'))
        batch_op.drop_index(batch_op.f('ix_tutor_threads_course_id'))
        batch_op.drop_index(batch_op.f('ix_tutor_threads_id'))
    op.drop_table('tutor_threads')

