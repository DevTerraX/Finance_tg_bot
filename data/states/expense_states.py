from aiogram.dispatcher.filters.state import State, StatesGroup

class ExpenseStates(StatesGroup):
    sum = State()
    category = State()
    confirm = State()
    edit = State()
    check = State()
