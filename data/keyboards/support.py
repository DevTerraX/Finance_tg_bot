from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from .main_menu import BACK_BUTTON
from .settings import AUTO_CLEAN_PREFIX


SUPPORT_ALLOW_TAG_YES = "✅ Да"
SUPPORT_ALLOW_TAG_NO = "❌ Нет"
SUPPORT_CONFIRM_BUTTON = "✅ Подтверждение"


def get_support_name_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(BACK_BUTTON))
    return keyboard


def get_support_tag_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton(SUPPORT_ALLOW_TAG_YES), KeyboardButton(SUPPORT_ALLOW_TAG_NO))
    keyboard.add(KeyboardButton(BACK_BUTTON))
    return keyboard


def get_support_issue_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton(BACK_BUTTON))
    return keyboard


def get_support_confirmation_keyboard(clean_chat_enabled: bool) -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    status = "Вкл" if clean_chat_enabled else "Выкл"
    keyboard.row(KeyboardButton(f"{AUTO_CLEAN_PREFIX}: {status}"))
    keyboard.row(KeyboardButton(SUPPORT_CONFIRM_BUTTON))
    keyboard.add(KeyboardButton(BACK_BUTTON))
    return keyboard
