from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from .main_menu import BACK_BUTTON


PROFILE_BUTTON = "👤 Профиль"
EXPENSE_CATEGORIES_BUTTON = "📂 Категории расходов"
INCOME_CATEGORIES_BUTTON = "💰 Категории доходов"
NOTIFICATIONS_BUTTON = "🔔 Напоминания"
SUPPORT_BUTTON = "🆘 Поддержка"
AUTO_CLEAN_PREFIX = "🧹 Автоочистка"
CLEAN_MODE_PREFIX = "⚙️ Режим очистки"
CATEGORY_ADD_BUTTON = "➕ Добавить категорию"
CATEGORY_DELETE_BUTTON = "🗑️ Удалить категорию"
CANCEL_BUTTON = "Отмена"


def get_settings_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton(PROFILE_BUTTON), KeyboardButton(EXPENSE_CATEGORIES_BUTTON))
    keyboard.row(KeyboardButton(INCOME_CATEGORIES_BUTTON), KeyboardButton(NOTIFICATIONS_BUTTON))
    keyboard.row(KeyboardButton(SUPPORT_BUTTON))
    keyboard.row(KeyboardButton(BACK_BUTTON))
    return keyboard


def get_profile_keyboard(user) -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton(f"{AUTO_CLEAN_PREFIX}: {'Вкл' if user.clean_chat else 'Выкл'}"))
    mode = getattr(user, "cleanup_mode", "standard")
    mode_label = "Стандарт" if mode == "standard" else "Агрессивно"
    keyboard.row(KeyboardButton(f"{CLEAN_MODE_PREFIX}: {mode_label}"))
    keyboard.row(KeyboardButton("✏️ Изменить имя"), KeyboardButton(f"💱 Валюта: {user.currency}"))
    keyboard.row(KeyboardButton(f"🌍 Часовой пояс: {user.timezone}"))
    keyboard.row(KeyboardButton(f"📅 Формат даты: {user.date_format}"))
    keyboard.row(KeyboardButton(BACK_BUTTON))
    return keyboard


def get_notifications_keyboard(user) -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton(f"🔔 Напоминания: {'Вкл' if user.daily_reminder_enabled else 'Выкл'}"))
    keyboard.row(KeyboardButton(f"⏰ Время напоминания: {user.reminder_time}"))
    keyboard.row(KeyboardButton(BACK_BUTTON))
    return keyboard


def get_category_management_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton(CATEGORY_ADD_BUTTON), KeyboardButton(CATEGORY_DELETE_BUTTON))
    keyboard.row(KeyboardButton(BACK_BUTTON))
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(CANCEL_BUTTON))
    return keyboard
