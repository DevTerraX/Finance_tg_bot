from __future__ import annotations

from datetime import datetime

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from ..utils.db_utils import (
    get_or_create_user,
    get_categories,
    create_category,
    create_transaction
)
from ..utils.validation import validate_amount
from ..utils.cleanup import clean_chat
from ..utils.storage import get_user_file_path, ensure_user_dirs
from ..keyboards.category import get_categories_keyboard
from ..keyboards.confirmation import get_confirmation_keyboard, get_edit_keyboard
from ..keyboards.main_menu import (
    get_main_menu,
    get_back_keyboard,
    BACK_BUTTON,
    EXPENSE_BUTTON
)
from ..states.expense_states import ExpenseStates
from ..models.category import Category


async def start_expense(message: types.Message, state: FSMContext):
    await state.finish()
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await ExpenseStates.sum.set()
    await state.update_data(user_id=user.id)
    await message.answer("🧾 Введи сумму расхода (например, 123.45):", reply_markup=get_back_keyboard())


async def expense_sum(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    if message.text == BACK_BUTTON:
        await state.finish()
        reply = await message.answer("🔙 Хорошо, возвращаю тебя в главное меню.", reply_markup=get_main_menu())
        if user.clean_chat:
            await clean_chat(message.bot, message.chat.id, reply.message_id)
        return
    try:
        amount = validate_amount(message.text)
    except ValueError as exc:
        await message.answer(f"⚠️ {exc} Попробуй ещё раз.", reply_markup=get_back_keyboard())
        return

    await state.update_data(amount=amount)
    await ExpenseStates.category.set()
    categories = await get_categories(user, 'expense')
    keyboard = get_categories_keyboard(categories)
    await message.answer("🏷️ Выбери категорию для этого расхода:", reply_markup=keyboard)


async def expense_category_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = query.data
    if data.startswith('select_category_'):
        cat_id = int(data.split('_')[-1])
        category = await Category.get(id=cat_id)
        await state.update_data(category_id=cat_id, category_name=category.name)
        await ExpenseStates.confirm.set()
        state_data = await state.get_data()
        amount = state_data['amount']
        await query.message.edit_text(
            f"✍️ Подтвердим расход?\n"
            f"💸 Сумма: {amount:.2f}\n"
            f"🏷️ Категория: {category.name}",
            reply_markup=get_confirmation_keyboard()
        )
    elif data == 'create_category':
        await ExpenseStates.category.set()
        await query.message.delete()
        await query.message.answer("🆕 Как назовём новую категорию?", reply_markup=get_back_keyboard())
    elif data == 'back':
        await state.finish()
        await query.message.delete()
        reply = await query.message.answer("🏠 Возвращаю в главное меню.", reply_markup=get_main_menu())
        if user.clean_chat:
            await clean_chat(query.bot, query.message.chat.id, reply.message_id)


async def expense_create_category(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    if message.text == BACK_BUTTON:
        await state.finish()
        reply = await message.answer("🔙 Готово, возвращаю тебя в главное меню.", reply_markup=get_main_menu())
        if user.clean_chat:
            await clean_chat(message.bot, message.chat.id, reply.message_id)
        return

    name = message.text.strip()
    category = await create_category(user, name, 'expense')
    await state.update_data(category_id=category.id, category_name=category.name)
    await ExpenseStates.confirm.set()
    state_data = await state.get_data()
    await message.answer(
        f"🌟 Категория '{name}' создана!\n"
        f"Подтверди расход на {state_data['amount']:.2f} {user.currency}.",
        reply_markup=get_confirmation_keyboard()
    )


async def expense_confirm_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    state_data = await state.get_data()

    if data == 'confirm':
        tx = await create_transaction(
            user,
            state_data['amount'],
            state_data['category_id'],
            'expense',
            state_data.get('check'),
            state_data.get('check_photo_path')
        )
        await state.finish()
        await query.message.edit_text("✅ Расход записан!")
        summary_text = (
            f"💸 Потрачено: {tx.amount:.2f} {user.currency} в категории {tx.category_name}.\n"
            f"💼 Баланс теперь: {user.balance:.2f} {user.currency}"
        )
        if state_data.get('check_photo_path'):
            summary_text += "\n🖼️ Фото чека прикреплено."
        elif state_data.get('check'):
            summary_text += "\n📝 Заметка к операции сохранена."

        reply = await query.message.answer(summary_text, reply_markup=get_main_menu())

        if user.clean_chat:
            await clean_chat(query.bot, query.message.chat.id, reply.message_id)
    elif data == 'edit':
        await ExpenseStates.edit.set()
        await query.message.edit_text("✏️ Что хочешь подправить?", reply_markup=get_edit_keyboard())
    elif data == 'add_check':
        await ExpenseStates.check.set()
        await query.message.delete()
        await query.message.answer(
            "📸 Пришли чек: можно фото или текст.",
            reply_markup=get_back_keyboard()
        )
    elif data == 'back':
        await ExpenseStates.category.set()
        categories = await get_categories(user, 'expense')
        await query.message.edit_text("🏷️ Выбери категорию:", reply_markup=get_categories_keyboard(categories))


async def expense_edit_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    if data == 'edit_sum':
        await ExpenseStates.sum.set()
        await query.message.delete()
        await query.message.answer("✨ Введи новую сумму расхода:", reply_markup=get_back_keyboard())
    elif data == 'edit_category':
        await ExpenseStates.category.set()
        user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
        categories = await get_categories(user, 'expense')
        await query.message.edit_text("🏷️ Выбери другую категорию:", reply_markup=get_categories_keyboard(categories))
    elif data == 'back':
        await ExpenseStates.confirm.set()
        state_data = await state.get_data()
        category_name = state_data.get('category_name', '—')
        await query.message.edit_text(
            f"✍️ Подтвердим расход?\n"
            f"💸 Сумма: {state_data['amount']:.2f}\n"
            f"🏷️ Категория: {category_name}",
            reply_markup=get_confirmation_keyboard()
        )


async def expense_check(message: types.Message, state: FSMContext):
    if message.text == BACK_BUTTON:
        await ExpenseStates.confirm.set()
        state_data = await state.get_data()
        category_name = state_data.get('category_name', '—')
        await message.answer(
            f"✍️ Подтвердим расход?\n"
            f"💸 Сумма: {state_data['amount']:.2f}\n"
            f"🏷️ Категория: {category_name}",
            reply_markup=get_confirmation_keyboard()
        )
        return

    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    ensure_user_dirs(user.id)

    if message.photo:
        photo = message.photo[-1]
        filename = f"expense_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        destination = get_user_file_path(user.id, "checks", filename)
        await photo.download(destination_file=str(destination))
        await state.update_data(
            check_photo_path=str(destination),
            check=message.caption.strip() if message.caption else None
        )
        await message.answer("📎 Фото чека закреплено. Подтверди операцию.", reply_markup=get_confirmation_keyboard())
    else:
        note = message.text.strip()
        await state.update_data(check=note, check_photo_path=None)
        await message.answer("📝 Заметка сохранена. Подтверди операцию.", reply_markup=get_confirmation_keyboard())
    await ExpenseStates.confirm.set()


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_expense, lambda m: m.text == EXPENSE_BUTTON, state="*")
    dp.register_message_handler(expense_sum, state=ExpenseStates.sum)
    dp.register_callback_query_handler(expense_category_callback, state=ExpenseStates.category)
    dp.register_message_handler(expense_create_category, state=ExpenseStates.category, content_types=['text'])
    dp.register_callback_query_handler(expense_confirm_callback, state=ExpenseStates.confirm)
    dp.register_callback_query_handler(expense_edit_callback, state=ExpenseStates.edit)
    dp.register_message_handler(expense_check, state=ExpenseStates.check, content_types=['text', 'photo'])
