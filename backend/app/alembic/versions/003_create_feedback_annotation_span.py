"""create feedback and annotation_span tables

Revision ID: 003
Revises: 002
Create Date: 2026-06-15 00:00:00.000000

"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("text_snapshot", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["message.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedback_message_id"), "feedback", ["message_id"])
    op.create_index(op.f("ix_feedback_user_id"), "feedback", ["user_id"])

    op.create_table(
        "annotation_span",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("feedback_id", sa.Uuid(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
        sa.Column("highlighted_text", sa.Text(), nullable=False),
        sa.Column(
            "tag",
            sa.Enum(
                "hallucination",
                "personal-information",
                "too-verbose",
                "high-priority",
                "low-priority",
                "others",
                name="annotationtag",
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["feedback_id"], ["feedback.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_annotation_span_feedback_id"), "annotation_span", ["feedback_id"]
    )
    op.create_index(op.f("ix_annotation_span_tag"), "annotation_span", ["tag"])


def downgrade():
    op.drop_index(op.f("ix_annotation_span_tag"), table_name="annotation_span")
    op.drop_index(op.f("ix_annotation_span_feedback_id"), table_name="annotation_span")
    op.drop_table("annotation_span")
    op.execute("DROP TYPE IF EXISTS annotationtag")
    op.drop_index(op.f("ix_feedback_user_id"), table_name="feedback")
    op.drop_index(op.f("ix_feedback_message_id"), table_name="feedback")
    op.drop_table("feedback")
