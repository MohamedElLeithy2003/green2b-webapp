"""Product views

Revision ID: f4db7c18b555
Revises: 4c8d507198ff
Create Date: 2025-08-07 12:38:35.355682

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4db7c18b555'
down_revision = '4c8d507198ff'
branch_labels = None
depends_on = None


def upgrade():

    # Then update foreign keys etc. as needed
    with op.batch_alter_table('product_views', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(None, 'product', ['product_id'], ['id'])

    with op.batch_alter_table('supplier_application', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.INTEGER(),
               nullable=False)

def downgrade():
    with op.batch_alter_table('product_views', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(None, 'product', ['product_id'], ['id'])
    with op.batch_alter_table('supplier_application', schema=None) as batch_op:
        batch_op.alter_column('user_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###
