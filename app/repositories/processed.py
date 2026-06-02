from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db import async_session
from app.models import ProcessedMessage


class ProcessedRepository:
    async def is_processed(self, user_id: int, message_id: str) -> bool:
        async with async_session() as session:
            result = await session.execute(
                select(ProcessedMessage.id).where(
                    ProcessedMessage.user_id == user_id,
                    ProcessedMessage.message_id == message_id,
                )
            )
            return result.first() is not None

    async def mark_processed(self, user_id: int, message_id: str) -> None:
        async with async_session() as session:
            session.add(ProcessedMessage(user_id=user_id, message_id=message_id))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()

    async def clear(self, user_id: int) -> None:
        async with async_session() as session:
            await session.execute(delete(ProcessedMessage).where(ProcessedMessage.user_id == user_id))
            await session.commit()
