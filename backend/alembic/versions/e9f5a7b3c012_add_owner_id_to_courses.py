"""add owner_id to courses

Revision ID: e9f5a7b3c012
Revises: d8e4f6a2b906
Create Date: 2026-10-12 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9f5a7b3c012'
down_revision: Union[str, Sequence[str], None] = 'd8e4f6a2b906'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('courses') as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f('ix_courses_owner_id'), ['owner_id'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('courses') as batch_op:
        batch_op.drop_index(batch_op.f('ix_courses_owner_id'))
        batch_op.drop_column('owner_id')

