# states/expense_states.py
from aiogram.dispatcher.filters.state import State, StatesGroup

class ExpenseStates(StatesGroup):
    sum = State()  # Ввод суммы (проверка на число)
    category = State()  # Выбор категории
    confirm = State()  # Подтверждение (сумма + категория)
    edit = State()  # Редактирование (сумма или категория)
    check = State()  # Добавление чека (фото или текст, опционально)