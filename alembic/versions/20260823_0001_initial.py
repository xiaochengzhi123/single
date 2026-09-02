"""Initial SignalTutor schema.

Revision ID: 20260823_0001
Revises:
"""

from sqlalchemy import inspect

from alembic import op
from signaltutor.db import models  # noqa: F401
from signaltutor.db.base import Base

revision = "20260823_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in reversed(inspect(bind).get_table_names()):
        if table_name != "alembic_version":
            op.drop_table(table_name)
