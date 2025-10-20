# keyboards/settings.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_settings_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура настроек"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📊 Категории расходов")],
            [KeyboardButton("💰 Категории доходов")],
            [KeyboardButton("🔙 Назад")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard

def get_categories_management_keyboard(categories, category_type) -> ReplyKeyboardMarkup:
    """Клавиатура управления категориями"""
    keyboard = []
    
    # Кнопки категорий (первые 3-4 для удобства)
    cat_buttons = []
    for i, category in enumerate(categories[:4]):
        cat_buttons.append(KeyboardButton(category['name']))
        if i % 2 == 1:  # Две кнопки в ряд
            keyboard.append(cat_buttons)
            cat_buttons = []
    
    if cat_buttons:
        keyboard.append(cat_buttons)
    
    # Если есть больше категорий, добавляем кнопку "Показать все"
    if len(categories) > 4:
        keyboard.append([KeyboardButton("📋 Показать все категории")])
    
    # Кнопки управления
    keyboard.extend([
        [KeyboardButton("➕ Добавить категорию")],
        [KeyboardButton("🗑️ Удалить категорию")],
        [KeyboardButton("🔙 Назад")]
    ])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_categories_delete_keyboard(categories, category_type) -> ReplyKeyboardMarkup:
    """Клавиатура для удаления категорий"""
    keyboard = []
    
    for i, category in enumerate(categories):
        row = []
        # Две категории в ряд
        if i % 2 == 0 and i + 1 < len(categories):
            row.append(KeyboardButton(f"🗑️ {categories[i]['name']}"))
            row.append(KeyboardButton(f"🗑️ {categories[i+1]['name']}"))
            i += 1
        else:
            row.append(KeyboardButton(f"🗑️ {category['name']}"))
        keyboard.append(row)
    
    keyboard.append([KeyboardButton("❌ Отмена")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
def get_categories_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Категория 1", callback_data="category_1"),
        InlineKeyboardButton("Категория 2", callback_data="category_2"),
        InlineKeyboardButton("Назад", callback_data="back")
    )
    return keyboard

def get_settings_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("Редактировать категории расходов"),
        KeyboardButton("Редактировать категории доходов"),
        KeyboardButton("Очистка чата"),  # Если есть настройка clean_chat
        KeyboardButton("Назад")
    )
    return keyboard