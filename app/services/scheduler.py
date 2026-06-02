import html
import logging
import os

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app import texts
from app.reply import send
from app.services.notifier import Notifier
from app.services.scanner import SubscriptionScanner
from app.repositories.users import UserRepository

logger = logging.getLogger(__name__)

DAILY_SCAN_HOUR = int(os.getenv("DAILY_SCAN_HOUR", "9"))
NOTIFY_HOUR = int(os.getenv("NOTIFY_HOUR", "10"))
NOTIFY_DAYS = tuple(int(d) for d in os.getenv("NOTIFY_DAYS", "3,2,1").split(","))


class SchedulerService:
    def __init__(
        self,
        bot: Bot,
        scanner: SubscriptionScanner,
        notifier: Notifier,
        user_repo: UserRepository,
    ):
        self.bot = bot
        self.scanner = scanner
        self.notifier = notifier
        self.user_repo = user_repo
        self.scheduler = AsyncIOScheduler()
        self._announced: set[int] = set()

    async def run_pending_initial_scans(self):
        users = await self.user_repo.list_pending_initial_scan()
        for u in users:
            if not u.oauth_token_json:
                continue
            uid = u.telegram_user_id
            if uid not in self._announced:
                self._announced.add(uid)
                await send(self.bot, uid, texts.SCAN_INITIAL_START)
            try:
                found, failed = await self.scanner.scan(uid, since_days=30, limit=50)
                if failed:
                    logger.warning(
                        "Первичный скан user_id=%s: %d писем не разобрано (проверь VPN), повтор позже",
                        uid, failed,
                    )
                    continue
                await self.user_repo.set_initial_scan_done(uid)
                self._announced.discard(uid)
                unique_count = len({s.id for s in found})
                await send(
                    self.bot, uid,
                    texts.SCAN_INITIAL_DONE.format(
                        count=unique_count,
                        days=", ".join(map(str, NOTIFY_DAYS)),
                    ),
                )
            except Exception as e:
                logger.error("Первичный скан не удался для user_id=%s: %s", uid, e)

    async def run_daily_scan(self):
        for u in await self.user_repo.list_all():
            if not u.oauth_token_json or not u.initial_scan_done:
                continue
            uid = u.telegram_user_id
            try:
                found, _ = await self.scanner.scan(uid, since_days=2)
                if found:
                    names = ", ".join(dict.fromkeys(s.service_name for s in found))
                    await send(self.bot, uid, texts.SCAN_NEW.format(names=html.escape(names)))
            except Exception as e:
                logger.error("Ежедневный скан не удался для user_id=%s: %s", uid, e)

    async def run_notifications(self):
        try:
            await self.notifier.notify_upcoming(NOTIFY_DAYS)
        except Exception as e:
            logger.error("Рассылка уведомлений не удалась: %s", e)

    def start(self):
        self.scheduler.add_job(
            self.run_pending_initial_scans, "interval", minutes=1,
            id="pending_initial_scans", max_instances=1, coalesce=True,
        )
        self.scheduler.add_job(
            self.run_daily_scan, "cron", hour=DAILY_SCAN_HOUR,
            id="daily_scan", max_instances=1, coalesce=True,
        )
        self.scheduler.add_job(
            self.run_notifications, "cron", hour=NOTIFY_HOUR,
            id="notify_upcoming", max_instances=1, coalesce=True,
        )
        self.scheduler.start()
        logger.info(
            "Планировщик запущен: первичный скан (каждую минуту), "
            "ежедневный скан (%02d:00), уведомления (%02d:00)",
            DAILY_SCAN_HOUR, NOTIFY_HOUR,
        )
