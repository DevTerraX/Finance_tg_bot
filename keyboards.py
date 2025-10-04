from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_wallets, get_categories

def get_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='💰 Баланс')],
            [KeyboardButton(text='💸 Внести расход')],
            [KeyboardButton(text='💵 Внести доход')],
            [KeyboardButton(text='📊 Итоги')],
            [KeyboardButton(text='⚙ Настройки')]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_summaries_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📅 Сегодня')],
            [KeyboardButton(text='📆 Неделя')],
            [KeyboardButton(text='📈 Месяц')],
            [KeyboardButton(text='🔎 Итог по категории')],
            [KeyboardButton(text='💳 Итог по кошельку')],
            [KeyboardButton(text='📤 Экспорт в CSV')],
            [KeyboardButton(text='📊 Круговая диаграмма')],
            [KeyboardButton(text='Назад')]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_settings_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='👜 Управление кошельками')],
            [KeyboardButton(text='📂 Управление категориями')],
            [KeyboardButton(text='🎯 Цели и лимиты')],
            [KeyboardButton(text='⏰ Напоминания')],
            [KeyboardButton(text='🔑 PIN-код')],
            [KeyboardButton(text='💾 Экспорт / бэкап БД')],
            [KeyboardButton(text='Назад')]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_categories_keyboard(kind):
    categories = get_categories(kind)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for emoji, name in categories:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=f"{emoji} {name}", callback_data=f"cat_{kind}_{name}")])
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="➕ Добавить", callback_data=f"add_cat_{kind}")])
    return keyboard

def get_wallets_keyboard():
    wallets = get_wallets()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for name in wallets:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text=name, callback_data=f"wallet_{name}")])
    return keyboard

def get_confirm_keyboard(kind):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data=f"confirm_{kind}")],
        [InlineKeyboardButton(text="Изменить", callback_data=f"change_{kind}")],
        [InlineKeyboardButton(text="Назад", callback_data=f"back_{kind}")]
    ])

def get_manage_keyboard(type_):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Добавить {type_}", callback_data=f"add_{type_}")],
        [InlineKeyboardButton(text=f"Удалить {type_}", callback_data=f"delete_{type_}")]
    ])