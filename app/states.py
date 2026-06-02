from aiogram.fsm.state import State, StatesGroup


class AddSub(StatesGroup):
    name = State()
    amount = State()
    currency = State()
    date = State()
    period = State()
