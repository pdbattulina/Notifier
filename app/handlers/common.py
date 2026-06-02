from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from app import texts
from app.reply import answer
from app.keyboards import MAIN_KB

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await answer(message, texts.START, image=texts.IMG_WELCOME, reply_markup=MAIN_KB)


@router.message(F.text == texts.MENU_ABOUT)
async def menu_about(message: Message, state: FSMContext):
    await state.clear()
    await answer(message, texts.ABOUT)
