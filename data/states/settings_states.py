from aiogram.dispatcher.filters.state import State, StatesGroup

class SettingsStates(StatesGroup):
    root = State()
    categories_menu = State()
    delete_category = State()
    add_category = State()
    profile_menu = State()
    edit_name = State()
    edit_currency = State()
    edit_timezone = State()
    edit_date_format = State()
    notifications_menu = State()
    edit_reminder_time = State()
