from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app import texts
from app.reply import answer
from app.keyboards import RECONNECT_KB, DISCONNECT_CONFIRM_KB
from app.container import oauth_service, gmail_service, user_repo, sub_repo, processed_repo

router = Router()


@router.message(F.text == texts.MENU_CONNECT)
async def menu_connect(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    service = None
    if await user_repo.exists(user_id):
        try:
            service = await gmail_service.get_service(user_id)
        except Exception:
            service = None

    if service:
        profile = await gmail_service.get_profile(service)
        await answer(
            message,
            texts.CHECK_OK.format(
                email=profile.get("emailAddress", "неизвестно"),
                total=profile.get("messagesTotal", 0),
            ),
            reply_markup=RECONNECT_KB,
        )
    else:
        auth_url = oauth_service.generate_auth_url(user_id)
        await answer(message, texts.AUTH_PROMPT.format(url=auth_url))


@router.callback_query(F.data == "disconnect_ask")
async def cb_disconnect_ask(callback: CallbackQuery):
    await callback.message.edit_text(texts.DISCONNECT_CONFIRM, reply_markup=DISCONNECT_CONFIRM_KB)
    await callback.answer()


@router.callback_query(F.data == "disconnect_yes")
async def cb_disconnect_yes(callback: CallbackQuery):
    user_id = callback.from_user.id
    await user_repo.disconnect(user_id)
    await sub_repo.delete_all(user_id)
    await processed_repo.clear(user_id)
    await callback.message.edit_text(texts.DISCONNECT_DONE)
    await callback.answer()
