import html

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from app import texts
from app.reply import answer
from app.container import user_repo, sub_repo
from app.keyboards import CURRENCY_KB, PERIOD_KB, CANCEL_KB
from app.states import AddSub
from app.repositories.subscriptions import parse_amount, parse_date

router = Router()


@router.message(F.text == texts.MENU_ADD)
async def menu_add(message: Message, state: FSMContext):
    await user_repo.ensure(message.from_user.id)
    await state.set_state(AddSub.name)
    await answer(message, texts.ADD_NAME, reply_markup=CANCEL_KB)


@router.callback_query(F.data == "menu_add")
async def cb_menu_add(callback: CallbackQuery, state: FSMContext):
    await user_repo.ensure(callback.from_user.id)
    await state.set_state(AddSub.name)
    await answer(callback.message, texts.ADD_NAME, reply_markup=CANCEL_KB)
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(texts.ADD_CANCELLED)
    await callback.answer()


@router.message(AddSub.name)
async def add_name(message: Message, state: FSMContext):
    if not message.text:
        await answer(message, texts.ADD_NAME_RETRY, reply_markup=CANCEL_KB)
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AddSub.amount)
    await answer(message, texts.ADD_AMOUNT, reply_markup=CANCEL_KB)


@router.message(AddSub.amount)
async def add_amount(message: Message, state: FSMContext):
    if not message.text:
        await answer(message, texts.ADD_AMOUNT_RETRY, reply_markup=CANCEL_KB)
        return
    raw = message.text.strip()
    if raw != "-":
        amount = parse_amount(raw.replace(",", "."))
        if amount is None:
            await answer(message, texts.ADD_AMOUNT_BAD, reply_markup=CANCEL_KB)
            return
        await state.update_data(amount=str(amount))
    await state.set_state(AddSub.currency)
    await answer(message, texts.ADD_CURRENCY, reply_markup=CURRENCY_KB)


@router.callback_query(AddSub.currency, F.data.startswith("cur:"))
async def add_currency(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":", 1)[1]
    if value != "-":
        await state.update_data(currency=value)
    await state.set_state(AddSub.date)
    await callback.message.edit_text(texts.ADD_DATE, reply_markup=CANCEL_KB)
    await callback.answer()


@router.message(AddSub.date)
async def add_date(message: Message, state: FSMContext):
    if not message.text:
        await answer(message, texts.ADD_DATE_RETRY, reply_markup=CANCEL_KB)
        return
    raw = message.text.strip()
    if raw != "-":
        if parse_date(raw) is None:
            await answer(message, texts.ADD_DATE_BAD, reply_markup=CANCEL_KB)
            return
        await state.update_data(billing_date=raw)
    await state.set_state(AddSub.period)
    await answer(message, texts.ADD_PERIOD, reply_markup=PERIOD_KB)


@router.callback_query(AddSub.period, F.data.startswith("per:"))
async def add_period(callback: CallbackQuery, state: FSMContext):
    period = callback.data.split(":", 1)[1]
    data = await state.get_data()
    payload = {
        "service_name": data.get("name"),
        "amount": data.get("amount"),
        "currency": data.get("currency"),
        "billing_date": data.get("billing_date"),
        "billing_period": period,
        "is_subscription": True,
    }
    sub = await sub_repo.upsert(callback.from_user.id, payload, source_message_id=None)
    await state.clear()
    await callback.message.edit_text(texts.ADD_DONE.format(service=html.escape(sub.service_name)))
    await callback.answer()
