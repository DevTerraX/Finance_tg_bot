from aiogram.dispatcher.filters.state import State, StatesGroup


class HistoryStates(StatesGroup):
    type = State()
    list = State()
    detail = State()
    edit_amount = State()
    edit_category = State()
    period_mode = State()
    period_input = State()
