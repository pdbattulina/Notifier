import calendar
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import delete, select

from app.db import async_session
from app.models import Subscription


def normalize_name(name: str) -> str:
    text = (name or "").lower().strip()
    text = re.sub(r"\.(com|ru|io|net|org)\b", "", text)
    text = text.replace("+", " ").replace(".", " ")
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_amount(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def format_amount(amount: Decimal | None, currency: str | None) -> str:
    if amount is None:
        return "сумма неизвестна"
    a = int(amount) if amount == amount.to_integral_value() else amount
    return f"{a} {currency or ''}".strip()


def _add_months(d: date, n: int) -> date:
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    day = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, day)


def next_billing_date(anchor: date | None, period: str | None, today: date | None = None) -> date | None:
    if anchor is None:
        return None
    today = today or date.today()
    if anchor >= today:
        return anchor
    p = (period or "").lower()
    nxt = anchor
    guard = 0
    while nxt < today and guard < 1000:
        if p == "monthly":
            nxt = _add_months(nxt, 1)
        elif p == "yearly":
            nxt = _add_months(nxt, 12)
        elif p == "weekly":
            nxt = nxt + timedelta(days=7)
        else:
            return anchor
        guard += 1
    return nxt


_PERIOD_RU = {"monthly": "неизвестно (месячная подписка)", "yearly": "неизвестно (годовая подписка)", "weekly": "неизвестно (недельная подписка)"}


_MONTHS_RU = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)


def format_date_ru(d: date) -> str:
    return f"{d.day} {_MONTHS_RU[d.month - 1]} {d.year} года"


def format_next_charge(anchor: date | None, period: str | None) -> str:
    nxt = next_billing_date(anchor, period)
    if nxt is not None:
        return format_date_ru(nxt)
    return _PERIOD_RU.get((period or "").lower(), "неизвестно")


class SubscriptionRepository:
    async def upsert(self, user_id: int, data: dict, source_message_id: str | None = None) -> Subscription:
        raw_name = (data.get("service_name") or "Unknown").strip()
        norm = normalize_name(raw_name) or "unknown"

        amount = parse_amount(data.get("amount"))
        currency = data.get("currency")
        billing_date = parse_date(data.get("billing_date"))
        billing_period = data.get("billing_period")

        async with async_session() as session:
            existing = (
                await session.execute(
                    select(Subscription).where(
                        Subscription.user_id == user_id,
                        Subscription.normalized_name == norm,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                existing.service_name = raw_name
                if amount is not None:
                    existing.amount = amount
                if currency:
                    existing.currency = currency
                if billing_date:
                    existing.billing_date = billing_date
                if billing_period:
                    existing.billing_period = billing_period
                existing.source_message_id = source_message_id
                existing.is_active = True
                sub = existing
            else:
                sub = Subscription(
                    user_id=user_id,
                    service_name=raw_name,
                    normalized_name=norm,
                    amount=amount,
                    currency=currency,
                    billing_date=billing_date,
                    billing_period=billing_period,
                    source_message_id=source_message_id,
                )
                session.add(sub)

            await session.commit()
            return sub

    async def list_by_user(self, user_id: int) -> list[Subscription]:
        async with async_session() as session:
            result = await session.execute(
                select(Subscription)
                .where(Subscription.user_id == user_id, Subscription.is_active.is_(True))
                .order_by(Subscription.billing_date)
            )
            return list(result.scalars().all())

    async def due_in_days(self, days: int) -> list[Subscription]:
        today = date.today()
        target = today + timedelta(days=days)
        async with async_session() as session:
            rows = (
                await session.execute(
                    select(Subscription).where(Subscription.is_active.is_(True))
                )
            ).scalars().all()
        return [
            s
            for s in rows
            if next_billing_date(s.billing_date, s.billing_period) == target
            and s.last_notified_on != today
        ]

    async def mark_notified(self, subscription_id: int, on_date: date) -> None:
        async with async_session() as session:
            sub = await session.get(Subscription, subscription_id)
            if sub:
                sub.last_notified_on = on_date
                await session.commit()

    async def delete(self, subscription_id: int, user_id: int) -> bool:
        async with async_session() as session:
            sub = await session.get(Subscription, subscription_id)
            if sub and sub.user_id == user_id:
                await session.delete(sub)
                await session.commit()
                return True
            return False

    async def delete_all(self, user_id: int) -> None:
        async with async_session() as session:
            await session.execute(delete(Subscription).where(Subscription.user_id == user_id))
            await session.commit()
