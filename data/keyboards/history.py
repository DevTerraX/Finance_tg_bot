from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime


def _format_datetime(dt: datetime) -> str:
    return dt.strftime("%d.%m %H:%M")


def get_history_type_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("➖ Расходы", callback_data="history_type_expense"),
        InlineKeyboardButton("➕ Доходы", callback_data="history_type_income"),
    )
    keyboard.add(InlineKeyboardButton("✖️ Закрыть", callback_data="history_close"))
    return keyboard


def get_transactions_keyboard(transactions):
    keyboard = InlineKeyboardMarkup(row_width=1)
    for tx in transactions:
        direction = "➖" if tx.type == "expense" else "➕"
        category = tx.category_name or "Без категории"
        button_text = f"{direction} {tx.amount:.2f} • {category} • {_format_datetime(tx.date)}"
        keyboard.add(InlineKeyboardButton(button_text, callback_data=f"history_tx_{tx.id}"))
    keyboard.add(InlineKeyboardButton("📅 Выбрать период", callback_data="history_period"))
    keyboard.add(InlineKeyboardButton("↔️ Сменить тип", callback_data="history_change_type"))
    keyboard.add(InlineKeyboardButton("🔄 Обновить список", callback_data="history_refresh"))
    keyboard.add(InlineKeyboardButton("✖️ Закрыть", callback_data="history_close"))
    return keyboard


def get_history_period_mode_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🕒 Последние 24 часа", callback_data="history_period_24h"),
        InlineKeyboardButton("📅 Конкретный день", callback_data="history_period_day"),
        InlineKeyboardButton("📆 Диапазон дат", callback_data="history_period_range"),
        InlineKeyboardButton("🔙 К списку", callback_data="history_period_back"),
    )
    return keyboard


def get_transaction_actions_keyboard(transaction):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✏️ Изменить сумму", callback_data=f"history_edit_amount_{transaction.id}"),
        InlineKeyboardButton("🏷️ Изменить категорию", callback_data=f"history_edit_category_{transaction.id}")
    )
    keyboard.add(InlineKeyboardButton("🗑️ Удалить операцию", callback_data=f"history_delete_{transaction.id}"))
    keyboard.add(InlineKeyboardButton("🔙 К списку", callback_data="history_back"))
    return keyboard


def get_delete_confirmation_keyboard(tx_id: int):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Да, удалить", callback_data=f"history_delete_confirm_{tx_id}"),
        InlineKeyboardButton("❌ Оставить", callback_data="history_delete_cancel"),
    )
    keyboard.add(InlineKeyboardButton("🔙 К списку", callback_data="history_back"))
    return keyboard


def get_category_selection_keyboard(categories):
    keyboard = InlineKeyboardMarkup(row_width=2)
    for cat in categories:
        keyboard.add(InlineKeyboardButton(cat.name, callback_data=f"history_category_{cat.id}"))
    keyboard.add(InlineKeyboardButton("🔙 К операции", callback_data="history_category_back"))
    return keyboard
