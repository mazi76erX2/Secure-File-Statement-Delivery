"""add customer pdf salt

Revision ID: 4c7d2f1d9aab
Revises: 9f86e3d8e8b1
Create Date: 2026-03-20 13:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4c7d2f1d9aab"
down_revision: str | None = "9f86e3d8e8b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "customers", sa.Column("pdf_salt", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("customers", "pdf_salt")
