# keyboards/main_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Баланс", callback_data="balance"),
        InlineKeyboardButton("Добавить расход", callback_data="add_expense"),
        InlineKeyboardButton("Добавить доход", callback_data="add_income"),
        InlineKeyboardButton("Итоги", callback_data="summary"),
        InlineKeyboardButton("Настройки", callback_data="settings")
    )
    return keyboard