"""Add Celery task tracking to files.

Revision ID: ec9ce804f0f3
Revises: 81c7859739b6
Create Date: 2026-11-01 13:34:38.352469
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "ec9ce804f0f3"
down_revision: Union[str, Sequence[str], None] = "81c7859739b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add file indexing status and Celery task ID."""

    # 1. Add index_status as nullable temporarily.
    op.add_column(
        "files",
        sa.Column(
            "index_status",
            sa.String(),
            nullable=True,
        ),
    )

    # 2. Mark previously uploaded files as SUCCESS.
    op.execute("UPDATE files SET index_status = 'SUCCESS'")

    # 3. Make index_status required and set the default
    # for newly inserted files.
    op.alter_column(
        "files",
        "index_status",
        existing_type=sa.String(),
        nullable=False,
        server_default="PENDING",
    )

    # 4. Add nullable Celery task identifier.
    # Existing files will have task_id = NULL.
    op.add_column(
        "files",
        sa.Column(
            "task_id",
            sa.String(),
            nullable=True,
        ),
    )

    # 5. Ensure that task IDs are unique.
    op.create_unique_constraint(
        "uq_files_task_id",
        "files",
        ["task_id"],
    )


def downgrade() -> None:
    """Remove Celery task tracking columns."""

    op.drop_constraint(
        "uq_files_task_id",
        "files",
        type_="unique",
    )

    op.drop_column("files", "task_id")

    op.drop_column("files", "index_status")
