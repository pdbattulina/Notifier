import asyncio
import base64
import logging

from app.services.gmail import GmailService
from app.repositories.processed import ProcessedRepository
from app.repositories.subscriptions import SubscriptionRepository
from app.models import Subscription
from app.parser.gemini import parse_with_gemini
from app.parser.filter import is_subscription_candidate

logger = logging.getLogger(__name__)

GMAIL_SEARCH_QUERY = (
    "subscription OR renewal OR billing OR payment OR invoice OR receipt "
    "OR подписка OR списание OR оплата OR продление"
)

REQUEST_DELAY_SEC = 4


def _decode(data: str) -> str:
    if not data:
        return ""
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")


def get_body(message: dict) -> str:
    payload = message.get("payload", {})

    def from_parts(parts: list, mime: str) -> str:
        for part in parts:
            if part.get("mimeType") == mime:
                text = _decode(part.get("body", {}).get("data", ""))
                if text:
                    return text
            if "multipart" in part.get("mimeType", ""):
                text = from_parts(part.get("parts", []), mime)
                if text:
                    return text
        return ""

    parts = payload.get("parts", [])
    if parts:
        return from_parts(parts, "text/plain") or from_parts(parts, "text/html")
    return _decode(payload.get("body", {}).get("data", ""))


def get_header(message: dict, name: str) -> str:
    for h in message.get("payload", {}).get("headers", []):
        if h.get("name") == name:
            return h.get("value", "")
    return ""


class SubscriptionScanner:
    def __init__(
        self,
        gmail: GmailService,
        sub_repo: SubscriptionRepository,
        processed_repo: ProcessedRepository,
    ):
        self.gmail = gmail
        self.sub_repo = sub_repo
        self.processed_repo = processed_repo

    async def _process_one(self, user_id: int, service, mid: str) -> tuple[Subscription | None, bool]:
        """Возвращает (подписка_или_None, ok). ok=False — Gemini не разобрал письмо."""
        msg = await self.gmail.get_message_full(service, mid)
        subject = get_header(msg, "Subject")
        sender = get_header(msg, "From")
        email_date = get_header(msg, "Date")
        body = get_body(msg)

        if not is_subscription_candidate(subject, body):
            await self.processed_repo.mark_processed(user_id, mid)
            return None, True

        data = await asyncio.to_thread(parse_with_gemini, sender, subject, body, email_date)

        if data is None:
            return None, False

        await self.processed_repo.mark_processed(user_id, mid)

        if data.get("is_subscription"):
            sub = await self.sub_repo.upsert(user_id, data, source_message_id=mid)
            logger.info("Подписка: %s (%s %s)", sub.service_name, sub.amount, sub.currency)
            return sub, True
        return None, True

    async def _process_ids(self, user_id: int, service, msg_ids: list[str]) -> tuple[list[Subscription], int]:
        found: list[Subscription] = []
        failed = 0
        for mid in dict.fromkeys(msg_ids):
            if await self.processed_repo.is_processed(user_id, mid):
                continue
            sub, ok = await self._process_one(user_id, service, mid)
            if not ok:
                failed += 1
                logger.warning("Gemini не разобрал письмо %s, оставлено на повтор", mid)
            elif sub:
                found.append(sub)
            await asyncio.sleep(REQUEST_DELAY_SEC)
        return found, failed

    async def scan(self, user_id: int, since_days: int | None = None, limit: int = 50) -> tuple[list[Subscription], int]:
        service = await self.gmail.get_service(user_id)
        if not service:
            logger.warning("Нет Gmail-сервиса для user_id=%s (нужна авторизация)", user_id)
            return [], 0

        query = GMAIL_SEARCH_QUERY
        if since_days:
            query = f"({GMAIL_SEARCH_QUERY}) newer_than:{since_days}d"

        listing = await self.gmail.search_messages(service, query, max_results=limit)
        msg_ids = [m["id"] for m in listing.get("messages", [])]
        msg_ids.reverse()
        logger.info("Gmail вернул %d писем для user_id=%s", len(msg_ids), user_id)

        return await self._process_ids(user_id, service, msg_ids)
