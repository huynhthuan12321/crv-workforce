"""Create CRV workforce schema."""

from alembic import op

from source.database.models import Base

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLES = [
    "bot_heartbeat", "notification_outbox", "sync_outbox", "audit_logs",
    "output_items", "output_logs", "work_sessions", "pay_batches", "products",
    "rate_history", "invite_codes", "location_consents", "consent_texts", "employees",
]


def upgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].drop(bind, checkfirst=True)
