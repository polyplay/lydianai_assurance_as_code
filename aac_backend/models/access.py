from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import TimestampMixin, id_column


class User(TimestampMixin, Base):
    __tablename__ = "users"

    user_id: Mapped[str] = id_column("USER")
    username: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(240))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="inactive")
    global_roles_json: Mapped[list] = mapped_column(JSON, default=list)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[str] = id_column("ROLE")
    role_name: Mapped[str] = mapped_column(String(80), unique=True)


class ProjectMembership(Base):
    __tablename__ = "project_memberships"
    __table_args__ = (UniqueConstraint("project_id", "user_id", "role_id"),)

    project_membership_id: Mapped[str] = id_column("PMEM")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.role_id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
