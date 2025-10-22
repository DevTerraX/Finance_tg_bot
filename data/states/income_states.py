from aiogram.dispatcher.filters.state import State, StatesGroup

class IncomeStates(StatesGroup):
    sum = State()
    category = State()
    confirm = State()
    edit = State()
