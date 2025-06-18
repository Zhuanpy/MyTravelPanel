"""add visa_type_id to visalinks

Revision ID: add_visa_type_id
Revises: 
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_visa_type_id'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # 1. 添加新字段 visa_type_id
    op.add_column('visalinks', sa.Column('visa_type_id', sa.Integer(), nullable=True))
    
    # 2. 添加外键约束
    op.create_foreign_key(
        'fk_visalinks_visa_type_id',
        'visalinks', 'visa_types',
        ['visa_type_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # 3. 将字段设置为不可为空
    op.alter_column('visalinks', 'visa_type_id',
                    existing_type=sa.Integer(),
                    nullable=False)

def downgrade():
    # 1. 删除外键约束
    op.drop_constraint('fk_visalinks_visa_type_id', 'visalinks', type_='foreignkey')
    
    # 2. 删除字段
    op.drop_column('visalinks', 'visa_type_id') 