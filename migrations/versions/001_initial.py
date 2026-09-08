"""Исходная схема: PK/FK, уникальность и CHECK для практики SQL и проверки целостности."""

from alembic import op
import sqlalchemy as sa

from backend.config import settings

revision = "001"
down_revision = None


def upgrade():
    """Создать только таблицы текущего сервиса; FK к пользователю возможен лишь в единой БД."""
    if settings.service in {"all", "identity"}:
        op.create_table("users", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("email", sa.String(254), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", sa.String(20), nullable=False),
            sa.CheckConstraint("role IN ('user','operator')", name="users_role"))
        op.create_table("sessions", sa.Column("token_hash", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    if settings.service in {"all", "tickets"}:
        op.create_table("tickets", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("author_id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.Text(), nullable=False), sa.Column("priority", sa.String(10), nullable=False),
            sa.Column("status", sa.String(10), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("priority IN ('low','normal','high')", name="tickets_priority"),
            sa.CheckConstraint("status IN ('new','active','closed')", name="tickets_status"))
        op.create_table("comments", sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
            sa.Column("author_id", sa.Uuid(), nullable=False), sa.Column("text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
        op.create_index("ix_tickets_author_id", "tickets", ["author_id"])
        op.create_index("ix_tickets_status", "tickets", ["status"])
        op.create_index("ix_comments_ticket_id", "comments", ["ticket_id"])
        if settings.service == "all":
            op.create_foreign_key("tickets_author", "tickets", "users", ["author_id"], ["id"])
            op.create_foreign_key("comments_author", "comments", "users", ["author_id"], ["id"])


def downgrade():
    """Удалить таблицы в порядке зависимостей; это разрушительный откат только для одноразовой учебной БД."""
    if settings.service in {"all", "tickets"}:
        op.drop_table("comments")
        op.drop_table("tickets")
    if settings.service in {"all", "identity"}:
        op.drop_table("sessions")
        op.drop_table("users")
