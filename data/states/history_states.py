from aiogram.dispatcher.filters.state import State, StatesGroup


class HistoryStates(StatesGroup):
    list = State()
    detail = State()
    edit_amount = State()
    edit_category = State()
