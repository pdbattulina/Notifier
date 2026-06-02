from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app import texts

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=texts.MENU_SUBS), KeyboardButton(text=texts.MENU_ADD)],
        [KeyboardButton(text=texts.MENU_SCAN), KeyboardButton(text=texts.MENU_CONNECT)],
        [KeyboardButton(text=texts.MENU_ABOUT)],
    ],
    resize_keyboard=True,
)

CANCEL_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel")],
])

RECONNECT_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=texts.BTN_RECONNECT, callback_data="disconnect_ask")],
])

DISCONNECT_CONFIRM_KB = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=texts.BTN_DISCONNECT_YES, callback_data="disconnect_yes")],
    [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel")],
])

MENU_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text=texts.BTN_ADD, callback_data="menu_add"),
    InlineKeyboardButton(text=texts.BTN_DELETE, callback_data="menu_del"),
]])

CURRENCY_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text=texts.BTN_RUB, callback_data="cur:RUB"),
        InlineKeyboardButton(text=texts.BTN_USD, callback_data="cur:USD"),
        InlineKeyboardButton(text=texts.BTN_EUR, callback_data="cur:EUR"),
    ],
    [InlineKeyboardButton(text=texts.BTN_SKIP, callback_data="cur:-")],
    [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel")],
])

PERIOD_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text=texts.BTN_MONTHLY, callback_data="per:monthly"),
        InlineKeyboardButton(text=texts.BTN_YEARLY, callback_data="per:yearly"),
        InlineKeyboardButton(text=texts.BTN_WEEKLY, callback_data="per:weekly"),
    ],
    [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data="cancel")],
])


def delete_list_kb(subs) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.BTN_DELETE_ITEM.format(name=s.service_name), callback_data=f"del:{s.id}")]
        for s in subs
    ])
