"""empty message

Revision ID: 41e8fe778f21
Revises: 3bc37d72421d
Create Date: 2025-08-05 10:53:16.979162

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '41e8fe778f21'
down_revision = '3bc37d72421d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('supplier_application', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_supplier_application_user_id',
            'user',
            ['user_id'],
            ['id']
        )
    # Optional: You can backfill user_id here via raw SQL if you have default user or known value
    # e.g. op.execute("UPDATE supplier_application SET user_id = 1 WHERE user_id IS NULL")

    # If you want, you can defer adding FK constraint to another migration for SQLite compatibility

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.VARCHAR(length=8),
               type_=sa.String(length=50),
               nullable=True)


def downgrade():
    with op.batch_alter_table('supplier_application', schema=None) as batch_op:
        batch_op.drop_column('user_id')

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.String(length=50),
               type_=sa.VARCHAR(length=8),
               nullable=False)
