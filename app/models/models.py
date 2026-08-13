from datetime import UTC, datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlmodel import Column, Field, Index, Relationship, SQLModel, Text

from app.core.enums import RiskLevel, Role


class TimeStampMixin(SQLModel):
    """Base mixin for timestamp fields."""

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[arg-type]
        sa_column_kwargs={
            "nullable": False,
            "server_default": func.current_timestamp(),
        },
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_type=DateTime(timezone=True),  # type: ignore[arg-type]
        sa_column_kwargs={
            "nullable": False,
            "onupdate": func.current_timestamp(),
        },
    )


class User(TimeStampMixin, SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]
    id: UUID = Field(primary_key=True, default_factory=uuid4)

    username: str = Field(unique=True, min_length=3, max_length=50)
    password_hash: str

    role: Role = Field(default=Role.USER)
    must_change_password: bool = Field(
        default=True, description="User must change password after first login"
    )
    is_active: bool = Field(default=True)

    created_by: Optional[UUID] = Field(foreign_key="users.id", default=None)
    creator: Optional["User"] = Relationship(
        sa_relationship_kwargs={"remote_side": "User.id"}
    )

    created_users: list["User"] = Relationship(back_populates="creator")

    analyses: list["Analysis"] = Relationship(
        back_populates="user", cascade_delete=True, passive_deletes=True
    )

    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="user", cascade_delete=True, passive_deletes=True
    )


class Risk(SQLModel, table=True):
    __table_args__ = (Index("idx_analysis_risks", "analysis_id", "risk_level"),)

    id: Optional[int] = Field(primary_key=True, default=None)

    risk_level: RiskLevel = Field(default=RiskLevel.AVERAGE)
    description: str = Field(max_length=1000)

    analysis_id: int = Field(foreign_key="analysis.id", ondelete="CASCADE")

    analysis: "Analysis" = Relationship(back_populates="risks")


class Analysis(TimeStampMixin, SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, default=None)

    title: str = Field(max_length=200, index=True)
    description: str = Field(default=None, sa_column=Column(Text))

    text: str = Field(description="document text")

    risks: list[Risk] = Relationship(
        back_populates="analysis", cascade_delete=True, passive_deletes=True
    )

    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)

    user: "User" = Relationship(back_populates="analyses")


class RefreshToken(TimeStampMixin, SQLModel, table=True):
    """Refresh token model - inherits created_at and updated_at from TimeStampMixin."""

    id: UUID = Field(primary_key=True, default_factory=uuid4)
    token_hash: str = Field(index=True)  # Indexed for faster lookups

    # Token management
    is_revoked: bool = Field(default=False)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    last_used_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # IP Tracking
    created_ip: Optional[str] = Field(default=None, max_length=45)  # IPv6 max length
    last_used_ip: Optional[str] = Field(default=None, max_length=45)

    # Device Tracking
    user_agent: Optional[str] = Field(default=None, max_length=512)

    # Relationships
    user_id: Optional[UUID] = Field(
        foreign_key="users.id", ondelete="CASCADE", index=True
    )
    user: "User" = Relationship(back_populates="refresh_tokens")


__all__ = ["User", "Analysis", "Risk", "RefreshToken"]
