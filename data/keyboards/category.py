# keyboards/category.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def get_categories_keyboard(categories, type='expense', for_delete=False):
    keyboard = InlineKeyboardMarkup(row_width=3)
    for cat in categories:
        if for_delete:
            callback = f"delete_category_{cat.id}"
        else:
            callback = f"select_category_{cat.id}"
        keyboard.add(InlineKeyboardButton(cat.name, callback_data=callback))
    
    keyboard.add(InlineKeyboardButton("Создать категорию", callback_data="create_category"))
    keyboard.add(InlineKeyboardButton("Назад", callback_data="back"))
    return keyboard

def get_categories_management_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("Добавить категорию"),
        KeyboardButton("Удалить категорию"),
        KeyboardButton("Назад")
    )
    return keyboard

def get_categories_delete_keyboard(categories, type='expense'):
    keyboard = InlineKeyboardMarkup(row_width=3)  # Оставим inline для списка категорий
    for cat in categories:
        callback = f"delete_category_{cat.id}"
        keyboard.add(InlineKeyboardButton(cat.name, callback_data=callback))
    keyboard.add(InlineKeyboardButton("Назад", callback_data="back"))
    return keyboard