# states/settings_states.py
from aiogram.dispatcher.filters.state import State, StatesGroup

class SettingsStates(StatesGroup):
    categories_menu = State()  # Меню категорий (расходы/доходы)
    add_category = State()  # Добавление новой категории
    delete_category = State()  # Выбор категории для удаления