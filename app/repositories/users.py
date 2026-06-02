from sqlalchemy import select

from app.db import async_session
from app.models import User


class UserRepository:
    async def get(self, user_id: int) -> User | None:
        async with async_session() as session:
            return await session.get(User, user_id)

    async def exists(self, user_id: int) -> bool:
        return await self.get(user_id) is not None

    async def ensure(self, user_id: int) -> None:
        async with async_session() as session:
            if await session.get(User, user_id) is None:
                session.add(User(telegram_user_id=user_id))
                await session.commit()

    async def save_token(self, user_id: int, token_json: str) -> None:
        async with async_session() as session:
            user = await session.get(User, user_id)
            if user is None:
                user = User(telegram_user_id=user_id)
                session.add(user)
            user.oauth_token_json = token_json
            await session.commit()

    async def get_token_json(self, user_id: int) -> str | None:
        user = await self.get(user_id)
        return user.oauth_token_json if user else None

    async def set_email(self, user_id: int, email: str) -> None:
        async with async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.gmail_email = email
                await session.commit()

    async def disconnect(self, user_id: int) -> None:
        async with async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.oauth_token_json = None
                user.gmail_email = None
                user.initial_scan_done = False
                await session.commit()

    async def set_initial_scan_done(self, user_id: int, value: bool = True) -> None:
        async with async_session() as session:
            user = await session.get(User, user_id)
            if user:
                user.initial_scan_done = value
                await session.commit()

    async def list_pending_initial_scan(self) -> list[User]:
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.initial_scan_done.is_(False))
            )
            return list(result.scalars().all())

    async def list_all(self) -> list[User]:
        async with async_session() as session:
            result = await session.execute(select(User))
            return list(result.scalars().all())
