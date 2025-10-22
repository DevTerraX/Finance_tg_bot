from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from ..utils.db_utils import get_or_create_user, get_summary
from ..utils.cleanup import clean_chat
from ..utils.charts import generate_pie_chart
from ..utils.csv_export import export_transactions_to_csv
from ..utils.analytics import (
    get_top_categories,
    get_average_daily_expense,
    get_income_expense_dynamics
)
from ..utils.storage import ensure_user_dirs
from ..keyboards.main_menu import get_main_menu, get_back_keyboard, SUMMARY_BUTTON, BACK_BUTTON
from ..keyboards.summary import (
    get_summary_menu,
    get_period_mode_keyboard,
    get_chart_period_keyboard,
    SUMMARY_OVERVIEW_BUTTON,
    SUMMARY_CSV_BUTTON,
    SUMMARY_CHART_BUTTON,
    SUMMARY_TOP_BUTTON,
    SUMMARY_AVG_BUTTON,
    SUMMARY_DYNAMICS_BUTTON,
    SUMMARY_PERIOD_BUTTON,
    SUMMARY_BACK_BUTTON
)
from ..states.summary_states import SummaryStates


async def show_summary_menu(message: types.Message, state: FSMContext):
    await state.finish()
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    ensure_user_dirs(user.id)
    await message.answer("📊 Добро пожаловать в аналитический центр! Выбирай, что посмотрим.", reply_markup=get_summary_menu())


async def summary_text_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    text = message.text
    last_message: types.Message | None = None

    if text == SUMMARY_OVERVIEW_BUTTON:
        summary_data = await get_summary(user)
        response = (
            f"💼 Баланс сейчас: {summary_data['balance']:.2f} {user.currency}\n"
            f"💵 Доходов накоплено: {summary_data['income']:.2f} {user.currency}\n"
            f"💸 Расходов учтено: {summary_data['expense']:.2f} {user.currency}"
        )
        last_message = await message.answer(response, reply_markup=get_summary_menu())
    elif text == SUMMARY_CSV_BUTTON:
        path = await export_transactions_to_csv(user, timedelta(hours=24))
        if path:
            with open(path, 'rb') as file:
                await message.answer_document(file, caption="📥 Вот свежий CSV за последние 24 часа.")
            last_message = await message.answer("🧾 Файл отправлен. Можешь открыть его в любимом редакторе.", reply_markup=get_summary_menu())
        else:
            last_message = await message.answer("ℹ️ За прошедшие сутки операций не было.", reply_markup=get_summary_menu())
    elif text == SUMMARY_CHART_BUTTON:
        await message.answer(
            "📊 Выбери период для диаграммы расходов:",
            reply_markup=get_chart_period_keyboard()
        )
    elif text == SUMMARY_TOP_BUTTON:
        top_categories = await get_top_categories(user, days=30)
        if not top_categories:
            last_message = await message.answer("🔥 За последние 30 дней расходы не найдены — отличная экономия!", reply_markup=get_summary_menu())
        else:
            lines = [
                f"{idx}. {name}: {amount:.2f} {user.currency}"
                for idx, (name, amount) in enumerate(top_categories, start=1)
            ]
            leaderboard = "\n".join(lines)
            last_message = await message.answer("🔥 Топ трат за 30 дней:\n" + leaderboard, reply_markup=get_summary_menu())
    elif text == SUMMARY_AVG_BUTTON:
        avg = await get_average_daily_expense(user, days=7)
        if avg is None:
            last_message = await message.answer("📉 Пока недостаточно данных для расчета среднесуточных расходов.", reply_markup=get_summary_menu())
        else:
            last_message = await message.answer(
                f"📉 Среднесуточные расходы за 7 дней: {avg:.2f} {user.currency}",
                reply_markup=get_summary_menu()
            )
    elif text == SUMMARY_DYNAMICS_BUTTON:
        stats = await get_income_expense_dynamics(user, days=7)
        msg = (
            "📆 Сравниваем последние 7 дней с предыдущей неделей:\n"
            f"💵 Доходы: {stats['current_income']:.2f} {user.currency} ({stats['income_change']:+.2f} {user.currency})\n"
            f"💸 Расходы: {stats['current_expense']:.2f} {user.currency} ({stats['expense_change']:+.2f} {user.currency})"
        )
        last_message = await message.answer(msg, reply_markup=get_summary_menu())
    elif text == SUMMARY_PERIOD_BUTTON:
        await SummaryStates.period_mode.set()
        await message.answer(
            "🗓️ Выбери формат периода.",
            reply_markup=get_back_keyboard()
        )
        await message.answer(
            "✨ Нажми нужный вариант:",
            reply_markup=get_period_mode_keyboard()
        )
    elif text == SUMMARY_BACK_BUTTON:
        await state.finish()
        last_message = await message.answer("🏠 Возвращаю в главное меню.", reply_markup=get_main_menu())
    else:
        last_message = await message.answer("Пожалуйста, выбери действие из меню ниже.", reply_markup=get_summary_menu())

    if last_message and user.clean_chat:
        await clean_chat(message.bot, message.chat.id, last_message.message_id)


async def summary_period_mode_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = query.data
    if data == "period_day":
        await SummaryStates.period_input.set()
        await state.update_data(period_mode='day')
        await query.message.edit_text(
            "🗓️ Введи дату в формате ДД.ММ.ГГГГ (например, 25.12.2024).",
        )
    elif data == "period_range":
        await SummaryStates.period_input.set()
        await state.update_data(period_mode='range')
        await query.message.edit_text(
            "🗂️ Введи диапазон в формате ДД.ММ.ГГГГ–ДД.ММ.ГГГГ (например, 01.12.2024–07.12.2024).",
        )
    elif data == "period_back":
        await state.finish()
        await query.message.edit_text("❌ Период не выбран.")
        reply = await query.message.answer("📊 Возвращаемся к аналитике.", reply_markup=get_summary_menu())
        if user.clean_chat:
            await clean_chat(query.bot, query.message.chat.id, reply.message_id)
    await query.answer()


async def summary_period_input(message: types.Message, state: FSMContext):
    if message.text == BACK_BUTTON:
        await state.finish()
        reply = await message.answer("📊 Возвращаемся к выбору отчётов.", reply_markup=get_summary_menu())
        user_profile = await get_or_create_user(message.from_user.id, message.from_user.full_name)
        if user_profile.clean_chat:
            await clean_chat(message.bot, message.chat.id, reply.message_id)
        return

    data = await state.get_data()
    mode = data.get('period_mode')
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    try:
        if mode == 'day':
            start, end = _parse_single_day(message.text)
        elif mode == 'range':
            start, end = _parse_range(message.text)
        else:
            raise ValueError("Неизвестный режим.")
    except ValueError:
        await message.answer(
            "⚠️ Не удалось распознать дату. Проверь формат и попробуй снова.",
            reply_markup=get_back_keyboard()
        )
        return

    summary_data = await get_summary(user, start=start, end=end)
    display_end = end - timedelta(days=1)
    if not summary_data['incomes'] and not summary_data['expenses']:
        reply = await message.answer("📭 В выбранном периоде записей не найдено.", reply_markup=get_summary_menu())
    else:
        text = (
            f"📆 Сводка за {start:%d.%m.%Y} – {display_end:%d.%m.%Y}:\n"
            f"💵 Доходы: {summary_data['income']:.2f} {user.currency}\n"
            f"💸 Расходы: {summary_data['expense']:.2f} {user.currency}\n"
            f"💼 Баланс: {summary_data['balance']:.2f} {user.currency}"
        )
        reply = await message.answer(text, reply_markup=get_summary_menu())

    await state.finish()
    if user.clean_chat:
        await clean_chat(message.bot, message.chat.id, reply.message_id)


async def summary_chart_callback(query: types.CallbackQuery):
    data = query.data
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)

    if data == "chart_back":
        await query.message.edit_text("Диаграмма отменена.")
        reply = await query.message.answer("📊 Возвращаемся к списку опций.", reply_markup=get_summary_menu())
        if user.clean_chat:
            await clean_chat(query.bot, query.message.chat.id, reply.message_id)
        await query.answer()
        return

    days = 7 if data == "chart_week" else 30
    end = datetime.now()
    start = end - timedelta(days=days)
    summary_data = await get_summary(user, start=start, end=end)

    expenses = summary_data['expenses']
    if not expenses:
        reply = await query.message.answer("📭 За выбранный период расходов не найдено.", reply_markup=get_summary_menu())
        if user.clean_chat:
            await clean_chat(query.bot, query.message.chat.id, reply.message_id)
        await query.answer()
        return

    exp_data: dict[str, float] = {}
    for tx in expenses:
        cat = tx.category_name or 'Без категории'
        exp_data[cat] = exp_data.get(cat, 0.0) + tx.amount

    path = generate_pie_chart(exp_data, f"Расходы_{days}_дней", user.id)
    if path:
        with open(path, 'rb') as photo:
            await query.message.answer_photo(photo, caption=f"🎯 Распределение расходов за {days} дней")
    reply = await query.message.answer("Готово! Выбирай следующий пункт.", reply_markup=get_summary_menu())
    if user.clean_chat:
        await clean_chat(query.bot, query.message.chat.id, reply.message_id)
    await query.answer()


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
    dp.register_message_handler(show_summary_menu, lambda m: m.text == SUMMARY_BUTTON, state="*")
    dp.register_message_handler(
        summary_text_handler,
        lambda m: m.text in {
            SUMMARY_OVERVIEW_BUTTON,
            SUMMARY_CSV_BUTTON,
            SUMMARY_CHART_BUTTON,
            SUMMARY_TOP_BUTTON,
            SUMMARY_AVG_BUTTON,
            SUMMARY_DYNAMICS_BUTTON,
            SUMMARY_PERIOD_BUTTON,
            SUMMARY_BACK_BUTTON
        },
        state="*"
    )
    dp.register_callback_query_handler(summary_period_mode_callback, lambda c: c.data.startswith("period_"), state=SummaryStates.period_mode)
    dp.register_message_handler(summary_period_input, state=SummaryStates.period_input)
    dp.register_callback_query_handler(summary_chart_callback, lambda c: c.data.startswith("chart_"), state="*")
