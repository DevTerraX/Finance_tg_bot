from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("Баланс"),
        KeyboardButton("Добавить расход"),
        KeyboardButton("Добавить доход"),
        KeyboardButton("Итоги"),
        KeyboardButton("Настройки")
    )
    return keyboard

def get_back_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Назад"))
    return keyboard

def get_settings_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("Категории расходов"),
        KeyboardButton("Категории доходов"),
        KeyboardButton("Назад")
    )
    return keyboard