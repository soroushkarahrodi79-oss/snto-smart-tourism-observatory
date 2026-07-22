"""v3.0 identity and multi-tenancy: organizations, users, territory.org_id

Revision ID: f1a2b3c4d5e6
Revises: 147bc9e8341e
Create Date: 2026-07-22 21:20:00.000000

Additive only: ``territories.org_id`` is nullable, so pre-tenancy rows (the
``pnsg`` default) stay valid and unowned until an organization claims them.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '147bc9e8341e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(),
            server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True,
    )
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(),
            server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False,
        ),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_org_id'), 'users', ['org_id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Additive tenancy link on territories; batch mode keeps it portable to
    # SQLite (dev) as well as PostgreSQL (production).
    with op.batch_alter_table('territories') as batch:
        batch.add_column(sa.Column('org_id', sa.Integer(), nullable=True))
        batch.create_index(
            op.f('ix_territories_org_id'), ['org_id'], unique=False,
        )
        batch.create_foreign_key(
            'fk_territories_org_id_organizations', 'organizations',
            ['org_id'], ['id'],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('territories') as batch:
        batch.drop_constraint(
            'fk_territories_org_id_organizations', type_='foreignkey',
        )
        batch.drop_index(op.f('ix_territories_org_id'))
        batch.drop_column('org_id')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_org_id'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_organizations_slug'), table_name='organizations')
    op.drop_table('organizations')
