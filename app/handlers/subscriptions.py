import html
import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app import texts
from app.reply import answer
from app.container import user_repo, sub_repo, scanner
from app.keyboards import MENU_KB, delete_list_kb
from app.repositories.subscriptions import format_amount, format_next_charge

router = Router()


async def send_delete_list(user_id: int, target: Message):
    subs = await sub_repo.list_by_user(user_id)
    if not subs:
        await answer(target, texts.SUBS_NONE_DELETE)
        return
    await answer(target, texts.SUBS_CHOOSE_DELETE, reply_markup=delete_list_kb(subs))


@router.message(F.text == texts.MENU_SUBS)
async def menu_subscriptions(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if not await user_repo.exists(user_id):
        await answer(message, texts.NOT_CONNECTED)
        return

    subs = await sub_repo.list_by_user(user_id)
    if not subs:
        await answer(message, texts.SUBS_EMPTY, image=texts.IMG_SUBSCRIPTIONS, reply_markup=MENU_KB)
        return

    lines = [texts.SUBS_HEADER]
    for s in subs:
        lines.append(
            texts.SUBS_LINE.format(
                service=html.escape(s.service_name),
                amount=html.escape(format_amount(s.amount, s.currency)),
                charge=html.escape(format_next_charge(s.billing_date, s.billing_period)),
            )
        )
    await answer(message, "\n".join(lines), image=texts.IMG_SUBSCRIPTIONS, reply_markup=MENU_KB)


@router.message(F.text == texts.MENU_SCAN)
async def menu_scan(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    user = await user_repo.get(user_id)
    if not user or not user.oauth_token_json:
        await answer(message, texts.NOT_CONNECTED)
        return

    await answer(message, texts.SCAN_START)
    try:
        since_days = 7 if user.initial_scan_done else 30
        found, failed = await scanner.scan(user_id, since_days=since_days, limit=50)
    except Exception as e:
        logging.exception("Ручная проверка почты не удалась")
        await answer(message, texts.SCAN_ERROR.format(error=e))
        return

    if found:
        names = ", ".join(dict.fromkeys(s.service_name for s in found))
        await answer(message, texts.SCAN_DONE.format(names=html.escape(names)))
    elif failed:
        await answer(message, texts.SCAN_PARTIAL)
    else:
        await answer(message, texts.SCAN_NOTHING)


@router.callback_query(F.data == "menu_del")
async def cb_menu_del(callback: CallbackQuery):
    await send_delete_list(callback.from_user.id, callback.message)
    await callback.answer()


@router.callback_query(F.data.startswith("del:"))
async def cb_delete(callback: CallbackQuery):
    sub_id = int(callback.data.split(":", 1)[1])
    ok = await sub_repo.delete(sub_id, callback.from_user.id)
    await callback.message.edit_text(texts.SUB_DELETED if ok else texts.SUB_NOT_FOUND)
    await callback.answer()
