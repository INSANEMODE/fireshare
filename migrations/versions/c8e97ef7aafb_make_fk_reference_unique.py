"""empty message

Revision ID: c8e97ef7aafb
Revises: d5598643eeee
Create Date: 2022-06-06 22:16:54.479210

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8e97ef7aafb'
down_revision = 'd5598643eeee'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_video_video_id', table_name='video')
    op.create_index(op.f('ix_video_video_id'), 'video', ['video_id'], unique=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_video_video_id'), table_name='video')
    op.create_index('ix_video_video_id', 'video', ['video_id'], unique=False)
    # ### end Alembic commands ###