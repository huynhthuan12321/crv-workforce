"""Create users table"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, comment="PK record"),
        sa.Column(
            "user_id",
            sa.BigInteger,
            nullable=False,
            unique=True,
            comment="External user ID (e.g. Telegram ID)",
        ),
        sa.Column(
            "role",
            sa.Enum("user", "admin", "moderator", name="userrole"),
            nullable=False,
            server_default="user",
            comment="User role",
        ),
        sa.Column(
            "language_code",
            sa.String(length=2),
            nullable=True,
            server_default="en",
            comment="Language code",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Created at",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment="Updated at",
        ),
    )


def downgrade() -> None:
    op.drop_table("users")
    userrole = sa.Enum("user", "admin", "moderator", name="userrole")
    userrole.drop(op.get_bind(), checkfirst=True)
