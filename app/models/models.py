from datetime import UTC, datetime
from typing import List
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlalchemy.types import DateTime
from sqlmodel import Column, Field, Index, Relationship, SQLModel, Text

from app.core.enums import RiskLevel, Role


class TimeStampMixin(SQLModel):
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), onupdate=func.current_timestamp()),
    )


class Users(TimeStampMixin, SQLModel, table=True):
    id: UUID | None = Field(primary_key=True, default=uuid4)

    username: str = Field(unique=True, min_length=3, max_length=50)
    password_hash: str

    role: Role = Field(default=Role.USER)
    must_change_password: bool = Field(
        default=True, description="User must change password after first login"
    )
    is_active: bool = Field(default=True)

    created_by: UUID | None = Field(foreign_key="users.id", default=None)
    creator: Users | None = Relationship(
        sa_relationship_kwargs={"remote_side": "Users.id"}
    )

    created_users: List[Users] = Relationship(back_populates="creator")

    analyses: List["Analysis"] = Relationship(
        back_populates="user", cascade_delete=True, passive_deletes=True
    )

    refresh_tokens: List["RefreshToken"] = Relationship(
        back_populates="user", cascade_delete=True, passive_deletes=True
    )


class Risk(SQLModel, table=True):
    __table_args__ = (Index("idx_analysis_risks", "analysis_id", "risk_level"),)

    id: int | None = Field(primary_key=True, default=None)

    risk_level: RiskLevel = Field(default=RiskLevel.AVERAGE)
    description: str = Field(max_length=1000)

    analysis_id: int = Field(foreign_key="analysis.id", ondelete="CASCADE")

    analysis: "Analysis" = Relationship(back_populates="risks")


class Analysis(TimeStampMixin, SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)

    title: str = Field(max_length=200, index=True)
    description: str | None = Field(default=None)

    text: Text = Field(description="document text")

    risks: List[Risk] = Relationship(
        back_populates="analysis", cascade_delete=True, passive_deletes=True
    )

    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)

    user: "Users" = Relationship(back_populates="analyses")


class RefreshToken(SQLModel, table=True):
    id: UUID | None = Field(primary_key=True, default_factory=uuid4)
    token_hash: str = Field(index=True)  # Indexed for faster lookups

    # Token management
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
    )
    last_used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # IP Tracking
    created_ip: str | None = Field(default=None, max_length=45)  # IPv6 max length
    last_used_ip: str | None = Field(default=None, max_length=45)

    # Device Tracking
    user_agent: str | None = Field(default=None, max_length=512)
    device_type: str | None = Field(
        default=None, max_length=50
    )  # mobile, desktop, tablet
    browser: str | None = Field(default=None, max_length=100)
    os: str | None = Field(default=None, max_length=100)

    # Location (optional, if you want to track geo location)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)

    # Relationships
    user_id: UUID | None = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    user: "Users" = Relationship(back_populates="refresh_tokens")


__all__ = ["Users", "Analysis", "Risk", "RefreshToken"]
