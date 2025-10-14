# keyboards/summary.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_summary_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Простая сводка", callback_data="simple_summary"),
        InlineKeyboardButton("Расширенные итоги", callback_data="advanced_summary"),
        InlineKeyboardButton("Диаграмма", callback_data="chart"),
        InlineKeyboardButton("CSV-файл", callback_data="csv"),
        InlineKeyboardButton("Выбрать период", callback_data="period")
    )
    keyboard.add(InlineKeyboardButton("Назад", callback_data="back_to_menu"))
    return keyboard