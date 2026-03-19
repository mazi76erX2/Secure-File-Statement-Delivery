"""add customer id number hash

Revision ID: 9f86e3d8e8b1
Revises: 7f5f6ac6ba92
Create Date: 2026-03-16 20:12:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9f86e3d8e8b1"
down_revision: str | None = "7f5f6ac6ba92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("id_number_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "id_number_hash")
