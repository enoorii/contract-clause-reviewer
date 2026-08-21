from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum
from sqlmodel import Column, Field, Relationship, SQLModel, Text, func
from typing_extensions import Optional

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

    created_by: UUID | None = Field(foreign_key="users.id", default=None)
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


class Analysis(TimeStampMixin, SQLModel, table=True):
    id: int = Field(primary_key=True, default=None)

    # Basic info (provided by user)
    title: str = Field(max_length=200, index=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    text: str = Field(description="document text")

    # Task tracking (for lookup)
    task_id: str | None = Field(default=None, index=True, max_length=255)

    # Analysis results (from LegalDocumentAnalysis)
    document_summary: str = Field(default="", sa_column=Column(Text))
    document_type: str = Field(default="", max_length=100)
    overall_risk_score: int = Field(default=0)
    recommendations: list[str] = Field(default=[], sa_column=Column(JSON))

    # Report generation
    report_stored: bool = Field(default=False)
    report_path: str | None = Field(default=None, nullable=True)
    report_generated_at: datetime = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    report_task_id: str | None = Field(
        default=None, max_length=255, index=True, nullable=True
    )

    # Relationships
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    user: "User" = Relationship(back_populates="analyses")

    clauses: list["Clause"] = Relationship(
        back_populates="analysis", cascade_delete=True, passive_deletes=True
    )


class Clause(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)

    clause_type: str = Field(max_length=100)
    summary: str = Field(sa_column=Column(Text))
    risk_level: RiskLevel = Field(
        default=RiskLevel.AVERAGE, sa_column=Column(Enum(RiskLevel, create_type=True))
    )
    key_terms: list[str] = Field(default=[], sa_column=Column(JSON))
    suggested_actions: list[str] = Field(default=[], sa_column=Column(JSON))

    analysis_id: int = Field(foreign_key="analysis.id", ondelete="CASCADE")
    analysis: "Analysis" = Relationship(back_populates="clauses")


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
    last_used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # IP Tracking
    created_ip: str | None = Field(default=None, max_length=45)  # IPv6 max length
    last_used_ip: str | None = Field(default=None, max_length=45)

    # Device Tracking
    user_agent: str | None = Field(default=None, max_length=512)

    # Relationships
    user_id: UUID | None = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    user: "User" = Relationship(back_populates="refresh_tokens")


__all__ = ["User", "Analysis", "Clause", "RefreshToken"]
