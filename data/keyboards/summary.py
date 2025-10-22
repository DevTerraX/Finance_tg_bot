from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from .main_menu import BACK_BUTTON


SUMMARY_OVERVIEW_BUTTON = "📈 Обзор кошелька"
SUMMARY_CSV_BUTTON = "🧾 CSV за сутки"
SUMMARY_CHART_BUTTON = "📊 Диаграмма расходов"
SUMMARY_TOP_BUTTON = "🔥 Топ категорий"
SUMMARY_AVG_BUTTON = "📉 Среднесуточные расходы"
SUMMARY_DYNAMICS_BUTTON = "💹 Динамика доходов/расходов"
SUMMARY_PERIOD_BUTTON = "📅 Выбрать период"
SUMMARY_BACK_BUTTON = BACK_BUTTON


def get_summary_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(
        KeyboardButton(SUMMARY_OVERVIEW_BUTTON),
        KeyboardButton(SUMMARY_CSV_BUTTON)
    )
    keyboard.row(
        KeyboardButton(SUMMARY_CHART_BUTTON),
        KeyboardButton(SUMMARY_TOP_BUTTON)
    )
    keyboard.row(
        KeyboardButton(SUMMARY_AVG_BUTTON),
        KeyboardButton(SUMMARY_DYNAMICS_BUTTON)
    )
    keyboard.row(KeyboardButton(SUMMARY_PERIOD_BUTTON))
    keyboard.row(KeyboardButton(SUMMARY_BACK_BUTTON))
    return keyboard


def get_period_mode_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📅 Один день", callback_data="period_day"),
        InlineKeyboardButton("📆 Диапазон дат", callback_data="period_range"),
        InlineKeyboardButton("🔙 Назад", callback_data="period_back")
    )
    return keyboard


def get_chart_period_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📆 7 дней", callback_data="chart_week"),
        InlineKeyboardButton("🗓️ 30 дней", callback_data="chart_month"),
        InlineKeyboardButton("🔙 Назад", callback_data="chart_back")
    )
    return keyboard
