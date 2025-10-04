from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import Category, Wallet
from tortoise.contrib.pydantic import pydantic_model_creator
from tortoise.exceptions import DoesNotExist

def get_main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(KeyboardButton('💰 Баланс'))
    keyboard.add(KeyboardButton('💸 Внести расход'))
    keyboard.add(KeyboardButton('💵 Внести доход'))
    keyboard.add(KeyboardButton('📊 Итоги'))
    keyboard.add(KeyboardButton('⚙ Настройки'))
    return keyboard

def get_summaries_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton('📅 Сегодня', callback_data='summary_day'))
    keyboard.add(InlineKeyboardButton('📆 Неделя', callback_data='summary_week'))
    keyboard.add(InlineKeyboardButton('📈 Месяц', callback_data='summary_month'))
    keyboard.add(InlineKeyboardButton('🔎 Итог по категории', callback_data='category_summary'))
    keyboard.add(InlineKeyboardButton('💳 Итог по кошельку', callback_data='wallet_summary'))
    keyboard.add(InlineKeyboardButton('📤 Экспорт в CSV', callback_data='export_csv'))
    keyboard.add(InlineKeyboardButton('📊 Круговая диаграмма', callback_data='pie_chart'))
    keyboard.add(InlineKeyboardButton('Назад', callback_data='back_main'))
    return keyboard

def get_settings_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton('👜 Управление кошельками', callback_data='manage_wallets'))
    keyboard.add(InlineKeyboardButton('📂 Управление категориями', callback_data='manage_categories'))
    keyboard.add(InlineKeyboardButton('🎯 Цели и лимиты', callback_data='manage_goals'))
    keyboard.add(InlineKeyboardButton('⏰ Напоминания', callback_data='set_reminder'))
    keyboard.add(InlineKeyboardButton('🔑 PIN-код', callback_data='set_pin'))
    keyboard.add(InlineKeyboardButton('💾 Экспорт / бэкап БД', callback_data='backup_db'))
    keyboard.add(InlineKeyboardButton('Назад', callback_data='back_main'))
    return keyboard

async def get_categories_keyboard(kind):
    categories = await Category.filter(kind__in=[kind, 'both']).all()
    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        keyboard.add(InlineKeyboardButton(text=f"{cat.emoji} {cat.name}", callback_data=f"cat_{kind}_{cat.name}"))
    keyboard.add(InlineKeyboardButton(text="Добавить", callback_data=f"add_cat_{kind}"))
    return keyboard

async def get_wallets_keyboard():
    wallets = await Wallet.all()
    keyboard = InlineKeyboardMarkup(row_width=2)
    for wallet in wallets:
        keyboard.add(InlineKeyboardButton(text=wallet.name, callback_data=f"wallet_{wallet.name}"))
    return keyboard

def get_confirm_keyboard(type_):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton('Подтвердить', callback_data=f"confirm_{type_}"))
    keyboard.add(InlineKeyboardButton('Изменить', callback_data=f"change_{type_}"))
    return keyboard

def get_manage_keyboard(type_):
    keyboard = InlineKeyboardMarkup(row_width=2)
    if type_ == 'wallet':
        keyboard.add(InlineKeyboardButton('Добавить', callback_data='add_wallet'))
        keyboard.add(InlineKeyboardButton('Удалить', callback_data='delete_wallet'))
    elif type_ == 'expense_category':
        keyboard.add(InlineKeyboardButton('Добавить', callback_data='add_expense_category'))
        keyboard.add(InlineKeyboardButton('Удалить', callback_data='delete_expense_category'))
    elif type_ == 'income_category':
        keyboard.add(InlineKeyboardButton('Добавить', callback_data='add_income_category'))
        keyboard.add(InlineKeyboardButton('Удалить', callback_data='delete_income_category'))
    return keyboard