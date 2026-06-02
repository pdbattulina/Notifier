from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    telegram_user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    gmail_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    oauth_token_json: Mapped[str | None] = mapped_column(String, nullable=True)
    initial_scan_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    processed_messages: Mapped[list["ProcessedMessage"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name", name="uq_user_service"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_user_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    service_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    billing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_notified_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="subscriptions")


class ProcessedMessage(Base):
    __tablename__ = "processed_messages"
    __table_args__ = (
        UniqueConstraint("user_id", "message_id", name="uq_user_message"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_user_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    message_id: Mapped[str] = mapped_column(String(64), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="processed_messages")
