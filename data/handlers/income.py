from __future__ import annotations

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from ..utils.db_utils import (
    get_or_create_user,
    get_categories,
    create_category,
    create_transaction,
    get_user_category,
)
from ..utils.validation import validate_amount
from ..utils.cleanup import schedule_cleanup, schedule_user_message_cleanup
from ..keyboards.category import get_categories_keyboard
from ..keyboards.confirmation import get_confirmation_keyboard, get_edit_keyboard
from ..keyboards.main_menu import (
    get_main_menu,
    get_back_keyboard,
    BACK_BUTTON,
    INCOME_BUTTON
)
from ..states.income_states import IncomeStates
async def start_income(message: types.Message, state: FSMContext):
    await state.finish()
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await IncomeStates.sum.set()
    await state.update_data(user_id=user.id)
    prompt = await message.answer("💰 Введи сумму дохода (например, 987.65):", reply_markup=get_back_keyboard())
    await schedule_cleanup(user, prompt, category="prompt", delete_history=True)


async def income_sum(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    if message.text == BACK_BUTTON:
        await state.finish()
        await message.answer("🔙 Хорошо, возвращаю тебя в главное меню.", reply_markup=get_main_menu())
        return
    try:
        amount = validate_amount(message.text)
    except ValueError as exc:
        error_message = await message.answer(f"⚠️ {exc} Попробуй ещё раз.", reply_markup=get_back_keyboard())
        await schedule_cleanup(user, error_message, category="prompt", delete_history=True)
        return

    await state.update_data(amount=amount)
    await IncomeStates.category.set()
    categories = await get_categories(user, 'income')
    keyboard = get_categories_keyboard(categories, type='income')
    prompt = await message.answer("🏷️ Выбери категорию для дохода:", reply_markup=keyboard)
    await schedule_cleanup(user, prompt, category="prompt", delete_history=True)


async def income_category_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    data = query.data
    if data.startswith('select_category_'):
        cat_id = int(data.split('_')[-1])
        category = await get_user_category(user, cat_id)
        if not category:
            await query.answer("Категория недоступна.", show_alert=True)
            return
        await state.update_data(category_id=cat_id, category_name=category.name)
        await IncomeStates.confirm.set()
        state_data = await state.get_data()
        amount = state_data['amount']
        await query.message.edit_text(
            f"✨ Подтвердим доход?\n"
            f"💵 Сумма: {amount:.2f}\n"
            f"🏷️ Категория: {category.name}",
            reply_markup=get_confirmation_keyboard(is_expense=False)
        )
    elif data == 'create_category':
        await IncomeStates.category.set()
        await query.message.delete()
        prompt = await query.message.answer("🆕 Как назовём новую категорию доходов?", reply_markup=get_back_keyboard())
        await schedule_cleanup(user, prompt, category="prompt", delete_history=True)
    elif data == 'back':
        await state.finish()
        await query.message.delete()
        await query.message.answer("🏠 Возвращаю в главное меню.", reply_markup=get_main_menu())


async def income_create_category(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    if message.text == BACK_BUTTON:
        await state.finish()
        await message.answer("🔙 Готово, возвращаю тебя в главное меню.", reply_markup=get_main_menu())
        return

    name = message.text.strip()
    category = await create_category(user, name, 'income')
    await state.update_data(category_id=category.id, category_name=category.name)
    await IncomeStates.confirm.set()
    state_data = await state.get_data()
    confirm_prompt = await message.answer(
        f"🌟 Категория '{name}' готова!\n"
        f"Подтверди доход на {state_data['amount']:.2f} {user.currency}.",
        reply_markup=get_confirmation_keyboard(is_expense=False)
    )
    await schedule_cleanup(user, confirm_prompt, category="prompt", delete_history=True)


async def income_confirm_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    state_data = await state.get_data()

    if data == 'confirm':
        try:
            tx = await create_transaction(
                user,
                state_data['amount'],
                state_data['category_id'],
                'income'
            )
        except ValueError as exc:
            await query.answer(str(exc), show_alert=True)
            return
        await state.finish()
        if query.message.text != "✅ Доход зафиксирован!":
            await query.message.edit_text("✅ Доход зафиксирован!")
        await schedule_cleanup(user, query.message, category="result", delete_history=False)
        summary_text = (
            f"💰 Поступило: {tx.amount:.2f} {user.currency} в категории {tx.category_name}.\n"
            f"💼 Баланс теперь: {user.balance:.2f} {user.currency}"
        )
        result_message = await query.message.answer(summary_text)
        await schedule_cleanup(user, result_message, category="result", delete_history=True)
        await query.message.answer("🔁 Главное меню", reply_markup=get_main_menu())
    elif data == 'edit':
        await IncomeStates.edit.set()
        await query.message.edit_text("✏️ Что хочешь подправить?", reply_markup=get_edit_keyboard())
    elif data == 'back':
        await IncomeStates.category.set()
        categories = await get_categories(user, 'income')
        await query.message.edit_text("🏷️ Выбери категорию:", reply_markup=get_categories_keyboard(categories, type='income'))


async def income_edit_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    if data == 'edit_sum':
        await IncomeStates.sum.set()
        await query.message.delete()
        prompt = await query.message.answer("✨ Введи новую сумму дохода:", reply_markup=get_back_keyboard())
        user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
        await schedule_cleanup(user, prompt, category="prompt", delete_history=True)
    elif data == 'edit_category':
        await IncomeStates.category.set()
        user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
        categories = await get_categories(user, 'income')
        await query.message.edit_text("🏷️ Выбери другую категорию:", reply_markup=get_categories_keyboard(categories, type='income'))
    elif data == 'back':
        await IncomeStates.confirm.set()
        state_data = await state.get_data()
        category_name = state_data.get('category_name', '—')
        await query.message.edit_text(
            f"✨ Подтвердим доход?\n"
            f"💵 Сумма: {state_data['amount']:.2f}\n"
            f"🏷️ Категория: {category_name}",
            reply_markup=get_confirmation_keyboard(is_expense=False)
        )


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_income, lambda m: m.text == INCOME_BUTTON, state="*")
    dp.register_message_handler(income_sum, state=IncomeStates.sum)
    dp.register_callback_query_handler(income_category_callback, state=IncomeStates.category)
    dp.register_message_handler(income_create_category, state=IncomeStates.category, content_types=['text'])
    dp.register_callback_query_handler(income_confirm_callback, state=IncomeStates.confirm)
    dp.register_callback_query_handler(income_edit_callback, state=IncomeStates.edit)
