from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

BALANCE_BUTTON = "💰 Баланс"
EXPENSE_BUTTON = "🧾 Добавить расход"
INCOME_BUTTON = "💵 Добавить доход"
SUMMARY_BUTTON = "📊 Итоги"
HISTORY_BUTTON = "📝 Операции"
SETTINGS_BUTTON = "⚙️ Настройки"
BACK_BUTTON = "🔙 Назад"


def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton(BALANCE_BUTTON), KeyboardButton(EXPENSE_BUTTON))
    keyboard.row(KeyboardButton(INCOME_BUTTON), KeyboardButton(SUMMARY_BUTTON))
    keyboard.row(KeyboardButton(HISTORY_BUTTON), KeyboardButton(SETTINGS_BUTTON))
    return keyboard


def get_back_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(BACK_BUTTON))
    return keyboard
