"""change annotation_span.tag from enum to varchar

Revision ID: 004
Revises: 003
Create Date: 2026-06-19 00:00:00.000000

SQLAlchemy inserts a str Enum's *name* (e.g. "too_verbose") into a native
PostgreSQL enum column rather than its *value* ("too-verbose"), causing an
InvalidTextRepresentation error. Switching to VARCHAR lets the Python enum
value roundtrip correctly without any SQLAlchemy workarounds.
"""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "annotation_span",
        "tag",
        type_=sa.String(),
        postgresql_using="tag::varchar",
        nullable=False,
    )
    op.execute("DROP TYPE IF EXISTS annotationtag")


def downgrade():
    op.execute(
        """
        CREATE TYPE annotationtag AS ENUM (
            'hallucination', 'personal-information', 'too-verbose',
            'high-priority', 'low-priority', 'others'
        )
        """
    )
    op.alter_column(
        "annotation_span",
        "tag",
        type_=sa.Enum(
            "hallucination",
            "personal-information",
            "too-verbose",
            "high-priority",
            "low-priority",
            "others",
            name="annotationtag",
        ),
        postgresql_using="tag::annotationtag",
        nullable=False,
    )
