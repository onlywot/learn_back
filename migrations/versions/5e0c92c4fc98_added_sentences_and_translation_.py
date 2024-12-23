"""Added sentences and translation sentences table

Revision ID: 5e0c92c4fc98
Revises: 56b46c418e8a
Create Date: 2024-10-08 22:16:42.124350

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5e0c92c4fc98'
down_revision: Union[str, None] = '56b46c418e8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('sentences',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('language_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['language_id'], ['languages.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('translation_sentences',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('sentence_id', sa.UUID(), nullable=False),
    sa.Column('from_language_id', sa.Integer(), nullable=False),
    sa.Column('to_language_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['from_language_id'], ['languages.id'], ),
    sa.ForeignKeyConstraint(['sentence_id'], ['sentences.id'], ),
    sa.ForeignKeyConstraint(['to_language_id'], ['languages.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('translation_sentences')
    op.drop_table('sentences')
    # ### end Alembic commands ###
