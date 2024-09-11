"""empty message

Revision ID: bab124384735
Revises: 
Create Date: 2024-09-05 18:01:15.300547

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bab124384735'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('translation_words',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('words',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('part_of_speech', sa.String(), nullable=False),
    sa.Column('rating', sa.String(), nullable=False),
    sa.Column('translation_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['translation_id'], ['translation_words.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('words')
    op.drop_table('translation_words')
    # ### end Alembic commands ###
