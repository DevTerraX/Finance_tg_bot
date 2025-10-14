# keyboards/category.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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