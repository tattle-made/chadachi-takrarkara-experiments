"""create oban tables (the background job queue)

Revision ID: 011
Revises: 010
Create Date: 2026-11-18

"""

from alembic import op
from oban.schema import install_sql, uninstall_sql


# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    # oban_jobs, oban_leaders, oban_producers and the oban_job_state type,
    # as the oban library defines them
    op.execute(install_sql())


def downgrade():
    op.execute(uninstall_sql())
