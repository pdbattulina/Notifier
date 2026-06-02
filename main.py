import asyncio
import logging
import sys
import os

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from app import texts
from app.container import user_repo, sub_repo, oauth_service, gmail_service, scanner
from app.services.notifier import Notifier
from app.services.scheduler import SchedulerService
from app.web import OAuthCallbackApp
from app.db import init_db
from app.handlers import common, auth, subscriptions, add

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(common.router)
dp.include_router(auth.router)
dp.include_router(subscriptions.router)
dp.include_router(add.router)

COMMANDS = [
    BotCommand(command="start", description=texts.CMD_START),
]


async def main():
    await init_db()
    logging.info("База данных инициализирована")

    callback_app = OAuthCallbackApp(oauth_service, gmail_service)
    await callback_app.start()

    notifier = Notifier(bot, sub_repo)
    SchedulerService(bot, scanner, notifier, user_repo).start()

    await bot.set_my_commands(COMMANDS)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
