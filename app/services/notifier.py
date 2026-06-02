import html
import logging
from datetime import date

from aiogram import Bot

from app import texts
from app.reply import send
from app.repositories.subscriptions import (
    SubscriptionRepository,
    format_amount,
    format_date_ru,
    next_billing_date,
)

logger = logging.getLogger(__name__)


def _days_word(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "дня"
    return "дней"


class Notifier:
    def __init__(self, bot: Bot, sub_repo: SubscriptionRepository):
        self.bot = bot
        self.sub_repo = sub_repo

    async def notify_upcoming(self, days_list: tuple[int, ...] = (3, 2, 1)) -> int:
        today = date.today()
        sent = 0
        for days in days_list:
            for s in await self.sub_repo.due_in_days(days):
                text = texts.NOTIFY.format(
                    days=days,
                    days_word=_days_word(days),
                    amount=html.escape(format_amount(s.amount, s.currency)),
                    service=html.escape(s.service_name),
                    date=format_date_ru(next_billing_date(s.billing_date, s.billing_period)),
                )
                try:
                    await send(self.bot, s.user_id, text)
                    await self.sub_repo.mark_notified(s.id, today)
                    sent += 1
                except Exception as e:
                    logger.error("Не удалось уведомить user_id=%s о %s: %s", s.user_id, s.service_name, e)
        logger.info("Уведомлений отправлено: %d", sent)
        return sent
