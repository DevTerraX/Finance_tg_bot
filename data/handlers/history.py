from __future__ import annotations

from contextlib import suppress

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageNotModified

from ..models.transaction import Transaction
from ..states.history_states import HistoryStates
from ..utils.cleanup import schedule_cleanup, schedule_user_message_cleanup
from ..utils.db_utils import (
    delete_transaction,
    get_categories,
    get_or_create_user,
    get_recent_transactions,
    get_transaction_by_id,
    update_transaction,
)
from ..utils.validation import validate_amount
from ..keyboards.history import (
    get_category_selection_keyboard,
    get_delete_confirmation_keyboard,
    get_transaction_actions_keyboard,
    get_transactions_keyboard,
)
from ..keyboards.main_menu import (
    BACK_BUTTON,
    HISTORY_BUTTON,
    get_back_keyboard,
    get_main_menu,
)


def _format_transaction_detail(tx: Transaction, currency: str) -> str:
    direction = "Расход" if tx.type == "expense" else "Доход"
    sign = "➖" if tx.type == "expense" else "➕"
    category = tx.category_name or "Без категории"
    lines = [
        f"{direction}: {sign} {tx.amount:.2f} {currency}",
        f"Категория: {category}",
        f"Дата: {tx.date:%d.%m.%Y %H:%M}",
    ]
    if tx.check:
        lines.append(f"Заметка: {tx.check}")
    if tx.check_photo_path:
        lines.append("Фото чека: прикреплено")
    return "\n".join(lines)


async def _show_transactions_list(bot: Bot, chat_id: int, message_id: int, user) -> bool:
    transactions = await get_recent_transactions(user, limit=10)
    if not transactions:
        try:
            await bot.edit_message_text(
                "Пока не найдено ни одной операции.",
                chat_id=chat_id,
                message_id=message_id,
            )
        except MessageNotModified:
            pass
        with suppress(MessageNotModified, Exception):
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
        return False

    text = (
        "📝 Последние операции.\n"
        "Выбери запись, чтобы изменить или удалить ее."
    )
    keyboard = get_transactions_keyboard(transactions)
    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=keyboard,
        )
    except MessageNotModified:
        with suppress(MessageNotModified):
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard,
            )
    return True


async def _show_transaction_detail(bot: Bot, chat_id: int, message_id: int, tx: Transaction, currency: str) -> None:
    text = _format_transaction_detail(tx, currency)
    keyboard = get_transaction_actions_keyboard(tx)
    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=keyboard,
        )
    except MessageNotModified:
        with suppress(MessageNotModified):
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard,
            )


async def show_history(message: types.Message, state: FSMContext):
    await state.finish()
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)

    transactions = await get_recent_transactions(user, limit=10)
    if not transactions:
        reply = await message.answer(
            "Пока еще нет операций, которые можно изменить или удалить.",
            reply_markup=get_main_menu(),
        )
        await schedule_cleanup(user, reply, category="prompt", delete_history=True)
        return

    await HistoryStates.list.set()
    list_message = await message.answer(
        "📝 Последние операции.\nВыбери запись, чтобы изменить или удалить ее.",
        reply_markup=get_transactions_keyboard(transactions),
    )
    await state.update_data(list_message_id=list_message.message_id)


async def history_refresh_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = await state.get_data()
    message_id = data.get("list_message_id", query.message.message_id)
    await _show_transactions_list(query.bot, query.message.chat.id, message_id, user)
    await state.update_data(list_message_id=message_id)
    await query.answer("Обновлено")


async def history_close_callback(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    with suppress(Exception):
        await query.message.edit_text("История закрыта.")
    reply = await query.message.answer("Возвращаю в главное меню.", reply_markup=get_main_menu())
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    await schedule_cleanup(user, reply, category="prompt", delete_history=True)
    await query.answer()


async def history_select_transaction(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    try:
        tx_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.answer("Не удалось определить операцию.", show_alert=True)
        return

    transaction = await get_transaction_by_id(user, tx_id)
    if not transaction:
        await query.answer("Операция не найдена.", show_alert=True)
        await _show_transactions_list(query.bot, query.message.chat.id, query.message.message_id, user)
        return

    await HistoryStates.detail.set()
    await state.update_data(
        list_message_id=query.message.message_id,
        selected_tx_id=transaction.id,
    )
    await _show_transaction_detail(query.bot, query.message.chat.id, query.message.message_id, transaction, user.currency)
    await query.answer()


async def history_back_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    await HistoryStates.list.set()
    await state.update_data(selected_tx_id=None)
    await _show_transactions_list(query.bot, query.message.chat.id, query.message.message_id, user)
    await query.answer()


async def history_edit_amount_callback(query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    try:
        tx_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.answer("Ошибка идентификатора.", show_alert=True)
        return

    transaction = await get_transaction_by_id(user, tx_id)
    if not transaction:
        await query.answer("Операция не найдена.", show_alert=True)
        await _show_transactions_list(query.bot, query.message.chat.id, data.get("list_message_id", query.message.message_id), user)
        return

    await HistoryStates.edit_amount.set()
    await state.update_data(selected_tx_id=transaction.id)
    prompt = await query.message.answer(
        "Введи новую сумму операции:",
        reply_markup=get_back_keyboard(),
    )
    await schedule_cleanup(user, prompt, category="prompt", delete_history=False)
    await query.answer()


async def history_amount_input(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    data = await state.get_data()
    list_message_id = data.get("list_message_id")
    selected_tx_id = data.get("selected_tx_id")

    if not list_message_id or not selected_tx_id:
        await state.finish()
        reply = await message.answer("Сессия редактирования завершена. Повтори попытку.", reply_markup=get_main_menu())
        await schedule_cleanup(user, reply, category="prompt", delete_history=True)
        return

    if message.text == BACK_BUTTON:
        transaction = await get_transaction_by_id(user, selected_tx_id)
        if transaction:
            await HistoryStates.detail.set()
            await _show_transaction_detail(message.bot, message.chat.id, list_message_id, transaction, user.currency)
        else:
            await HistoryStates.list.set()
            await _show_transactions_list(message.bot, message.chat.id, list_message_id, user)
        note = await message.answer("Изменение суммы отменено.")
        await schedule_cleanup(user, note, category="prompt", delete_history=True)
        return

    try:
        amount = validate_amount(message.text)
    except ValueError as exc:
        error = await message.answer(f"⚠️ {exc} Попробуй ещё раз.")
        await schedule_cleanup(user, error, category="prompt", delete_history=True)
        return

    transaction = await get_transaction_by_id(user, selected_tx_id)
    if not transaction:
        await HistoryStates.list.set()
        info = await message.answer("Операция не найдена. Обновляю список.", reply_markup=get_main_menu())
        await schedule_cleanup(user, info, category="prompt", delete_history=True)
        await _show_transactions_list(message.bot, message.chat.id, list_message_id, user)
        return

    await update_transaction(transaction, amount=amount)
    await HistoryStates.detail.set()
    await _show_transaction_detail(message.bot, message.chat.id, list_message_id, transaction, user.currency)
    reply = await message.answer("Сумма обновлена.")
    await schedule_cleanup(user, reply, category="prompt", delete_history=True)


async def history_edit_category_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    try:
        tx_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.answer("Ошибка идентификатора.", show_alert=True)
        return

    transaction = await get_transaction_by_id(user, tx_id)
    if not transaction:
        await query.answer("Операция не найдена.", show_alert=True)
        await HistoryStates.list.set()
        await _show_transactions_list(query.bot, query.message.chat.id, query.message.message_id, user)
        return

    categories = await get_categories(user, transaction.type)
    if not categories:
        await query.answer("Нет доступных категорий.", show_alert=True)
        return

    await HistoryStates.edit_category.set()
    await state.update_data(selected_tx_id=transaction.id)
    await query.message.edit_text(
        "Выбери новую категорию:",
        reply_markup=get_category_selection_keyboard(categories),
    )
    await query.answer()


async def history_category_select_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = await state.get_data()
    list_message_id = data.get("list_message_id", query.message.message_id)
    selected_tx_id = data.get("selected_tx_id")

    try:
        category_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.answer("Не удалось определить категорию.", show_alert=True)
        return

    if not selected_tx_id:
        await HistoryStates.list.set()
        await _show_transactions_list(query.bot, query.message.chat.id, list_message_id, user)
        await query.answer("Сессия редактирования устарела.", show_alert=True)
        return

    transaction = await get_transaction_by_id(user, selected_tx_id)
    if not transaction:
        await HistoryStates.list.set()
        await _show_transactions_list(query.bot, query.message.chat.id, list_message_id, user)
        await query.answer("Операция не найдена.", show_alert=True)
        return

    try:
        await update_transaction(transaction, category_id=category_id)
    except ValueError as exc:
        await query.answer(str(exc), show_alert=True)
        return
    await HistoryStates.detail.set()
    await _show_transaction_detail(query.bot, query.message.chat.id, list_message_id, transaction, user.currency)
    await query.answer("Категория обновлена.")


async def history_category_back_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    selected_tx_id = (await state.get_data()).get("selected_tx_id")
    if not selected_tx_id:
        await HistoryStates.list.set()
        await _show_transactions_list(query.bot, query.message.chat.id, query.message.message_id, user)
        await query.answer()
        return

    transaction = await get_transaction_by_id(user, selected_tx_id)
    if transaction:
        await HistoryStates.detail.set()
        await _show_transaction_detail(query.bot, query.message.chat.id, query.message.message_id, transaction, user.currency)
    else:
        await HistoryStates.list.set()
        await _show_transactions_list(query.bot, query.message.chat.id, query.message.message_id, user)
    await query.answer()


async def history_delete_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    try:
        tx_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.answer("Ошибка идентификатора.", show_alert=True)
        return

    transaction = await get_transaction_by_id(user, tx_id)
    if not transaction:
        await HistoryStates.list.set()
        await _show_transactions_list(query.bot, query.message.chat.id, query.message.message_id, user)
        await query.answer("Операция не найдена.", show_alert=True)
        return

    await HistoryStates.detail.set()
    await state.update_data(selected_tx_id=transaction.id)
    detail_text = (
        _format_transaction_detail(transaction, user.currency)
        + "\n\nУдалить эту операцию?"
    )
    try:
        await query.message.edit_text(
            detail_text,
            reply_markup=get_delete_confirmation_keyboard(transaction.id),
        )
    except MessageNotModified:
        await query.message.edit_reply_markup(get_delete_confirmation_keyboard(transaction.id))
    await query.answer()


async def history_delete_confirm_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = await state.get_data()
    list_message_id = data.get("list_message_id", query.message.message_id)

    try:
        tx_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.answer("Ошибка идентификатора.", show_alert=True)
        return

    transaction = await get_transaction_by_id(user, tx_id)
    if not transaction:
        await HistoryStates.list.set()
        await _show_transactions_list(query.bot, query.message.chat.id, list_message_id, user)
        await query.answer("Операция уже удалена.", show_alert=True)
        return

    await delete_transaction(transaction)
    await HistoryStates.list.set()
    has_records = await _show_transactions_list(query.bot, query.message.chat.id, list_message_id, user)
    if not has_records:
        await state.finish()
        reply = await query.message.answer("Все операции удалены. Возвращаю в главное меню.", reply_markup=get_main_menu())
        await schedule_cleanup(user, reply, category="prompt", delete_history=True)
    else:
        note = await query.message.answer("Операция удалена.")
        await schedule_cleanup(user, note, category="prompt", delete_history=True)
    await query.answer()


async def history_cancel_delete_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    selected_tx_id = (await state.get_data()).get("selected_tx_id")
    if not selected_tx_id:
        await HistoryStates.list.set()
        await _show_transactions_list(query.bot, query.message.chat.id, query.message.message_id, user)
        await query.answer()
        return

    transaction = await get_transaction_by_id(user, selected_tx_id)
    if transaction:
        await HistoryStates.detail.set()
        await _show_transaction_detail(query.bot, query.message.chat.id, query.message.message_id, transaction, user.currency)
    else:
        await HistoryStates.list.set()
        await _show_transactions_list(query.bot, query.message.chat.id, query.message.message_id, user)
    await query.answer("Удаление отменено.")


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(show_history, lambda m: m.text == HISTORY_BUTTON, state="*")
    dp.register_callback_query_handler(history_refresh_callback, lambda c: c.data == "history_refresh", state=HistoryStates.list)
    dp.register_callback_query_handler(history_close_callback, lambda c: c.data == "history_close", state="*")
    dp.register_callback_query_handler(history_select_transaction, lambda c: c.data.startswith("history_tx_"), state=HistoryStates.list)
    dp.register_callback_query_handler(history_back_callback, lambda c: c.data == "history_back", state=[HistoryStates.detail, HistoryStates.edit_amount, HistoryStates.edit_category])
    dp.register_callback_query_handler(history_edit_amount_callback, lambda c: c.data.startswith("history_edit_amount_"), state=HistoryStates.detail)
    dp.register_message_handler(history_amount_input, state=HistoryStates.edit_amount)
    dp.register_callback_query_handler(history_edit_category_callback, lambda c: c.data.startswith("history_edit_category_"), state=HistoryStates.detail)
    dp.register_callback_query_handler(history_category_select_callback, lambda c: c.data.startswith("history_category_"), state=HistoryStates.edit_category)
    dp.register_callback_query_handler(history_category_back_callback, lambda c: c.data == "history_category_back", state=HistoryStates.edit_category)
    dp.register_callback_query_handler(history_delete_callback, lambda c: c.data.startswith("history_delete_"), state=HistoryStates.detail)
    dp.register_callback_query_handler(history_delete_confirm_callback, lambda c: c.data.startswith("history_delete_confirm_"), state="*")
    dp.register_callback_query_handler(history_cancel_delete_callback, lambda c: c.data == "history_delete_cancel", state="*")
