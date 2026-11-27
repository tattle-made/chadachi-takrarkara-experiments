"""add reply_received_at to takedown_email ("Got a reply")

Revision ID: 012
Revises: 011
Create Date: 2026-11-19

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "dmca_email",
        sa.Column("reply_received_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("dmca_email", "reply_received_at")
