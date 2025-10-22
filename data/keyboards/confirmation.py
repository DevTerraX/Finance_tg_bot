from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_confirmation_keyboard(is_expense=True):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Подтвердить", callback_data="confirm"),
        InlineKeyboardButton("✏️ Редактировать", callback_data="edit")
    )
    if is_expense:
        keyboard.add(InlineKeyboardButton("📎 Добавить чек", callback_data="add_check"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back"))
    return keyboard

def get_edit_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💰 Сумма", callback_data="edit_sum"),
        InlineKeyboardButton("🏷️ Категория", callback_data="edit_category")
    )
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back"))
    return keyboard
