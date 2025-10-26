from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import MessageNotModified

from ..models.transaction import Transaction
from ..states.history_states import HistoryStates
from ..utils.cleanup import schedule_cleanup, schedule_user_message_cleanup, schedule_prompt_cleanup
from ..utils.db_utils import (
    delete_transaction,
    get_categories,
    get_or_create_user,
    get_transaction_by_id,
    update_transaction,
)
from ..utils.validation import validate_amount
from ..keyboards.history import (
    get_history_type_keyboard,
    get_history_period_mode_keyboard,
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


def _default_period() -> tuple[datetime, datetime]:
    end = datetime.now()
    start = end - timedelta(days=1)
    return start, end


def _deserialize_period(data: dict) -> tuple[datetime, datetime]:
    start_raw = data.get("period_start")
    end_raw = data.get("period_end")
    if start_raw and end_raw:
        try:
            return datetime.fromisoformat(start_raw), datetime.fromisoformat(end_raw)
        except ValueError:
            pass
    return _default_period()


def _format_period_label(mode: str, start: datetime, end: datetime) -> str:
    if mode == "24h":
        return "последние 24 часа"
    display_end = end - timedelta(seconds=1)
    if mode == "day":
        return f"{start:%d.%m.%Y}"
    return f"{start:%d.%m.%Y} – {display_end:%d.%m.%Y}"


def _type_title(tx_type: str) -> str:
    return "Расходы" if tx_type == "expense" else "Доходы"


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


async def _show_transactions_list(
    bot: Bot,
    chat_id: int,
    message_id: int,
    user,
    *,
    tx_type: str,
    start: datetime,
    end: datetime,
    mode: str,
) -> bool:
    transactions = await Transaction.filter(
        user=user,
        type=tx_type,
        date__gte=start,
        date__lt=end,
    ).order_by("-date").limit(10)
    period_label = _format_period_label(mode, start, end)
    title = _type_title(tx_type)
    if not transactions:
        text = f"Пока нет {title.lower()} за {period_label}."
        keyboard = get_transactions_keyboard([])
    else:
        text = (
            f"📝 {title} за {period_label}.\n"
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
    return bool(transactions)


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


def _extract_filters(data: dict) -> tuple[str | None, datetime, datetime, str]:
    tx_type = data.get("selected_type")
    start, end = _deserialize_period(data)
    mode = data.get("period_mode", "24h")
    return tx_type, start, end, mode


async def _render_list_from_state(
    state: FSMContext,
    bot: Bot,
    chat_id: int,
    message_id: int,
    user,
    data: dict | None = None,
) -> bool:
    state_data = data or await state.get_data()
    tx_type, start, end, mode = _extract_filters(state_data)
    if not tx_type:
        return False
    return await _show_transactions_list(
        bot,
        chat_id,
        message_id,
        user,
        tx_type=tx_type,
        start=start,
        end=end,
        mode=mode,
    )


async def show_history(message: types.Message, state: FSMContext):
    await state.finish()
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    await HistoryStates.type.set()
    type_message = await message.answer(
        "📝 Что показать? Выбери расходы или доходы.",
        reply_markup=get_history_type_keyboard(),
    )
    await state.update_data(list_message_id=type_message.message_id, selected_type=None, selected_tx_id=None)


async def history_type_select_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    tx_type = "expense" if query.data.endswith("expense") else "income"
    start, end = _default_period()
    await HistoryStates.list.set()
    await state.update_data(
        selected_type=tx_type,
        period_mode="24h",
        period_start=start.isoformat(),
        period_end=end.isoformat(),
        list_message_id=query.message.message_id,
        selected_tx_id=None,
    )
    await _show_transactions_list(
        query.bot,
        query.message.chat.id,
        query.message.message_id,
        user,
        tx_type=tx_type,
        start=start,
        end=end,
        mode="24h",
    )
    await query.answer("Показываю последние 24 часа")


async def history_refresh_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = await state.get_data()
    message_id = data.get("list_message_id", query.message.message_id)
    tx_type, start, end, mode = _extract_filters(data)
    if not tx_type:
        await HistoryStates.type.set()
        await query.message.edit_text(
            "📝 Что показать? Выбери расходы или доходы.",
            reply_markup=get_history_type_keyboard(),
        )
        await query.answer("Сначала выбери тип")
        return
    await _show_transactions_list(
        query.bot,
        query.message.chat.id,
        message_id,
        user,
        tx_type=tx_type,
        start=start,
        end=end,
        mode=mode,
    )
    await state.update_data(list_message_id=message_id)
    await query.answer("Обновлено")


async def history_change_type_callback(query: types.CallbackQuery, state: FSMContext):
    await HistoryStates.type.set()
    await state.update_data(selected_type=None, selected_tx_id=None, list_message_id=query.message.message_id)
    try:
        await query.message.edit_text(
            "📝 Что показать? Выбери расходы или доходы.",
            reply_markup=get_history_type_keyboard(),
        )
    except MessageNotModified:
        pass
    await query.answer()


async def history_period_open_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = await state.get_data()
    tx_type = data.get("selected_type")
    if not tx_type:
        await query.answer("Сначала выбери тип операций.", show_alert=True)
        return
    await HistoryStates.period_mode.set()
    prompt = await query.message.answer(
        "Выбери формат периода:",
        reply_markup=get_history_period_mode_keyboard(),
    )
    await query.answer()


async def history_period_mode_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = await state.get_data()
    tx_type = data.get("selected_type")
    list_message_id = data.get("list_message_id", query.message.message_id)
    action = query.data.split("_")[-1]

    if action == "back":
        await HistoryStates.list.set()
        with suppress(Exception):
            await query.message.delete()
        await query.answer()
        return

    if not tx_type:
        await HistoryStates.type.set()
        with suppress(Exception):
            await query.message.delete()
        await query.answer("Сначала выбери тип", show_alert=True)
        return

    if action == "24h":
        start, end = _default_period()
        await state.update_data(
            period_mode="24h",
            period_start=start.isoformat(),
            period_end=end.isoformat(),
        )
        await HistoryStates.list.set()
        with suppress(Exception):
            await query.message.delete()
        await _show_transactions_list(
            query.bot,
            query.message.chat.id,
            list_message_id,
            user,
            tx_type=tx_type,
            start=start,
            end=end,
            mode="24h",
        )
        await query.answer("Показаны последние 24 часа")
        return

    if action in {"day", "range"}:
        await HistoryStates.period_input.set()
        await state.update_data(period_mode=action)
        with suppress(Exception):
            await query.message.delete()
        prompt_text = (
            "📅 Введи дату в формате ДД.ММ.ГГГГ (например, 25.12.2024)."
            if action == "day"
            else "📆 Введи диапазон в формате ДД.ММ.ГГГГ–ДД.ММ.ГГГГ."
        )
        await query.message.answer(prompt_text, reply_markup=get_back_keyboard())
        await query.answer()


async def history_period_input(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    data = await state.get_data()
    list_message_id = data.get("list_message_id")
    period_mode = data.get("period_mode", "day")

    tx_type = data.get("selected_type")

    if not list_message_id or not tx_type:
        await state.finish()
        await message.answer("Сессия истории устарела. Открой операции заново.", reply_markup=get_main_menu())
        return

    if message.text == BACK_BUTTON:
        await HistoryStates.list.set()
        await _render_list_from_state(state, message.bot, message.chat.id, list_message_id, user, data)
        note = await message.answer("Период не изменён.")
        await schedule_cleanup(user, note, category="prompt", delete_history=True)
        return

    try:
        if period_mode == "day":
            start, end = _parse_single_day(message.text)
        else:
            start, end = _parse_range(message.text)
    except ValueError:
        error = await message.answer("⚠️ Не удалось распознать даты. Проверь формат и попробуй снова.", reply_markup=get_back_keyboard())
        await schedule_prompt_cleanup(user, error)
        return

    await state.update_data(
        period_start=start.isoformat(),
        period_end=end.isoformat(),
        period_mode=period_mode,
    )
    await HistoryStates.list.set()
    await _show_transactions_list(
        message.bot,
        message.chat.id,
        list_message_id,
        user,
        tx_type=tx_type,
        start=start,
        end=end,
        mode=period_mode,
    )
    confirm = await message.answer("Период обновлён.")
    await schedule_cleanup(user, confirm, category="prompt", delete_history=True)


async def history_close_callback(query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    with suppress(Exception):
        await query.message.edit_text("История закрыта.")
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    await query.message.answer("Возвращаю в главное меню.", reply_markup=get_main_menu())
    await query.answer()


async def history_select_transaction(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = await state.get_data()
    try:
        tx_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        await query.answer("Не удалось определить операцию.", show_alert=True)
        return

    transaction = await get_transaction_by_id(user, tx_id)
    if not transaction:
        await query.answer("Операция не найдена.", show_alert=True)
        await _render_list_from_state(state, query.bot, query.message.chat.id, query.message.message_id, user, data)
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
    await _render_list_from_state(state, query.bot, query.message.chat.id, query.message.message_id, user)
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
        await _render_list_from_state(
            state,
            query.bot,
            query.message.chat.id,
            data.get("list_message_id", query.message.message_id),
            user,
            data,
        )
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
        await message.answer("Сессия редактирования завершена. Повтори попытку.", reply_markup=get_main_menu())
        return

    if message.text == BACK_BUTTON:
        transaction = await get_transaction_by_id(user, selected_tx_id)
        if transaction:
            await HistoryStates.detail.set()
            await _show_transaction_detail(message.bot, message.chat.id, list_message_id, transaction, user.currency)
        else:
            await HistoryStates.list.set()
            await _render_list_from_state(state, message.bot, message.chat.id, list_message_id, user, data)
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
        await message.answer("Операция не найдена. Обновляю список.", reply_markup=get_main_menu())
        await _render_list_from_state(state, message.bot, message.chat.id, list_message_id, user, data)
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
        await _render_list_from_state(state, query.bot, query.message.chat.id, query.message.message_id, user)
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
        await _render_list_from_state(state, query.bot, query.message.chat.id, list_message_id, user, data)
        await query.answer("Сессия редактирования устарела.", show_alert=True)
        return

    transaction = await get_transaction_by_id(user, selected_tx_id)
    if not transaction:
        await HistoryStates.list.set()
        await _render_list_from_state(state, query.bot, query.message.chat.id, list_message_id, user, data)
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
        await _render_list_from_state(state, query.bot, query.message.chat.id, query.message.message_id, user)
        await query.answer()
        return

    transaction = await get_transaction_by_id(user, selected_tx_id)
    if transaction:
        await HistoryStates.detail.set()
        await _show_transaction_detail(query.bot, query.message.chat.id, query.message.message_id, transaction, user.currency)
    else:
        await HistoryStates.list.set()
        await _render_list_from_state(state, query.bot, query.message.chat.id, query.message.message_id, user)
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
        await _render_list_from_state(state, query.bot, query.message.chat.id, query.message.message_id, user)
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
        await _render_list_from_state(state, query.bot, query.message.chat.id, list_message_id, user, data)
        await query.answer("Операция уже удалена.", show_alert=True)
        return

    await delete_transaction(transaction)
    await HistoryStates.list.set()
    has_records = await _render_list_from_state(state, query.bot, query.message.chat.id, list_message_id, user)
    if not has_records:
        await state.finish()
        await query.message.answer("Все операции удалены. Возвращаю в главное меню.", reply_markup=get_main_menu())
    else:
        note = await query.message.answer("Операция удалена.")
        await schedule_cleanup(user, note, category="prompt", delete_history=True)
    await query.answer()


async def history_cancel_delete_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    selected_tx_id = (await state.get_data()).get("selected_tx_id")
    if not selected_tx_id:
        await HistoryStates.list.set()
        await _render_list_from_state(state, query.bot, query.message.chat.id, query.message.message_id, user)
        await query.answer()
        return

    transaction = await get_transaction_by_id(user, selected_tx_id)
    if transaction:
        await HistoryStates.detail.set()
        await _show_transaction_detail(query.bot, query.message.chat.id, query.message.message_id, transaction, user.currency)
    else:
        await HistoryStates.list.set()
        await _render_list_from_state(state, query.bot, query.message.chat.id, query.message.message_id, user)
        await query.answer("Удаление отменено.")


def _parse_single_day(text: str) -> tuple[datetime, datetime]:
    date_obj = datetime.strptime(text.strip(), "%d.%m.%Y")
    start = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end


def _parse_range(text: str) -> tuple[datetime, datetime]:
    normalized = text.replace('–', '-').replace('—', '-')
    parts = normalized.split('-')
    if len(parts) != 2:
        raise ValueError("Неверный формат диапазона")
    start = datetime.strptime(parts[0].strip(), "%d.%m.%Y")
    end = datetime.strptime(parts[1].strip(), "%d.%m.%Y") + timedelta(days=1)
    return start, end


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(show_history, lambda m: m.text == HISTORY_BUTTON, state="*")
    dp.register_callback_query_handler(history_type_select_callback, lambda c: c.data.startswith("history_type_"), state=HistoryStates.type)
    dp.register_callback_query_handler(history_refresh_callback, lambda c: c.data == "history_refresh", state=HistoryStates.list)
    dp.register_callback_query_handler(history_change_type_callback, lambda c: c.data == "history_change_type", state=HistoryStates.list)
    dp.register_callback_query_handler(history_period_open_callback, lambda c: c.data == "history_period", state=HistoryStates.list)
    dp.register_callback_query_handler(history_period_mode_callback, lambda c: c.data.startswith("history_period_"), state=HistoryStates.period_mode)
    dp.register_message_handler(history_period_input, state=HistoryStates.period_input)
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
