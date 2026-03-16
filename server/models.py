"""Module for defining the database models."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, func

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Customer(Base, TimestampMixin):
    """Customer profile for statement ownership."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    statements: Mapped[list["AccountStatement"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class AccountStatement(Base, TimestampMixin):
    """Stored PDF statement metadata for customer downloads."""

    __tablename__ = "account_statements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    account_number_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    statement_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    statement_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="application/pdf"
    )
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="statements")
    download_links: Mapped[list["StatementDownloadLink"]] = relationship(
        back_populates="statement", cascade="all, delete-orphan"
    )


class StatementDownloadLink(Base, TimestampMixin):
    """Secure, time-limited download links for statement files."""

    __tablename__ = "statement_download_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    statement_id: Mapped[int] = mapped_column(
        ForeignKey("account_statements.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    max_downloads: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_downloaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    statement: Mapped[AccountStatement] = relationship(back_populates="download_links")
