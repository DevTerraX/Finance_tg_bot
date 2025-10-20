from aiogram.dispatcher.filters.state import State, StatesGroup

class SettingsStates(StatesGroup):
    categories_menu = State()
    category_management = State()
    delete_category = State()
    add_category = State()