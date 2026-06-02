from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, Message

ASSETS = Path(__file__).resolve().parent / "assets"


def _photo(image: str | None) -> FSInputFile | None:
    if not image:
        return None
    path = ASSETS / image
    return FSInputFile(path) if path.exists() else None


async def answer(message: Message, text: str, image: str | None = None, **kwargs) -> None:
    photo = _photo(image)
    if photo:
        await message.answer_photo(photo, caption=text, **kwargs)
    else:
        await message.answer(text, **kwargs)


async def send(bot: Bot, chat_id: int, text: str, image: str | None = None, **kwargs) -> None:
    photo = _photo(image)
    if photo:
        await bot.send_photo(chat_id, photo, caption=text, **kwargs)
    else:
        await bot.send_message(chat_id, text, **kwargs)
