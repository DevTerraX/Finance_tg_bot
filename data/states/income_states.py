# states/income_states.py
from aiogram.dispatcher.filters.state import State, StatesGroup

class IncomeStates(StatesGroup):
    sum = State()  # Ввод суммы
    category = State()  # Выбор категории
    confirm = State()  # Подтверждение
    edit = State()  # Редактирование