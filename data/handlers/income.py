# data/handlers/income.py
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from ..utils.db_utils import get_or_create_user, get_categories, create_category, create_transaction
from ..utils.validation import validate_amount
from ..utils.cleanup import clean_chat
from ..keyboards.category import get_categories_keyboard
from ..keyboards.confirmation import get_confirmation_keyboard, get_edit_keyboard
from ..keyboards.main_menu import get_main_menu, get_back_keyboard
from ..states.income_states import IncomeStates
from ..models.category import Category

async def income_sum(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await state.finish()
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_menu())
        return

    user = await get_or_create_user(message.from_user.id)
    try:
        amount = validate_amount(message.text)
        await state.update_data(amount=amount)
        await IncomeStates.category.set()
        categories = await get_categories(user, 'income')
        keyboard = get_categories_keyboard(categories, type='income')
        await message.answer("Выберите категорию:", reply_markup=keyboard)
    except ValueError as e:
        await message.answer(str(e) + " Попробуйте снова.", reply_markup=get_back_keyboard())

async def income_category_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    if data.startswith('select_category_'):
        cat_id = int(data.split('_')[-1])
        await state.update_data(category_id=cat_id)
        await IncomeStates.confirm.set()
        state_data = await state.get_data()
        amount = state_data['amount']
        category = await Category.get(id=cat_id)
        await query.message.edit_text(f"Подтвердите: {amount} в категории {category.name}", reply_markup=get_confirmation_keyboard(is_expense=False))
    elif data == 'create_category':
        await IncomeStates.category.set()
        await query.message.edit_text("Введите название новой категории:", reply_markup=get_back_keyboard())
    elif data == 'back':
        await state.finish()
        await query.message.edit_text("Главное меню", reply_markup=get_main_menu())

async def income_create_category(message: types.Message, state: FSMContext):
    if message.text == "Назад":
        await state.finish()
        await message.answer("Возвращаемся в главное меню.", reply_markup=get_main_menu())
        return

    user = await get_or_create_user(message.from_user.id)
    name = message.text.strip()
    category = await create_category(user, name, 'income')
    await state.update_data(category_id=category.id)
    await IncomeStates.confirm.set()
    state_data = await state.get_data()
    await message.answer(f"Категория создана. Подтвердите: {state_data['amount']} в {name}", reply_markup=get_confirmation_keyboard(is_expense=False))

async def income_confirm_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    user = await get_or_create_user(query.from_user.id)
    state_data = await state.get_data()
    if data == 'confirm':
        await create_transaction(user, state_data['amount'], state_data['category_id'], 'income')
        await query.message.edit_text("Доход добавлен!")
        await state.finish()
        if user.clean_chat:
            await clean_chat(query.bot, query.message.chat.id, query.message.message_id)
    elif data == 'edit':
        await IncomeStates.edit.set()
        await query.message.edit_text("Что редактировать?", reply_markup=get_edit_keyboard())
    elif data == 'back':
        await IncomeStates.category.set()
        categories = await get_categories(user, 'income')
        await query.message.edit_text("Выберите категорию:", reply_markup=get_categories_keyboard(categories, type='income'))

async def income_edit_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    if data == 'edit_sum':
        await IncomeStates.sum.set()
        await query.message.edit_text("Введите новую сумму:", reply_markup=get_back_keyboard())
    elif data == 'edit_category':
        await IncomeStates.category.set()
        user = await get_or_create_user(query.from_user.id)
        categories = await get_categories(user, 'income')
        await query.message.edit_text("Выберите новую категорию:", reply_markup=get_categories_keyboard(categories, type='income'))
    elif data == 'back':
        await IncomeStates.confirm.set()
        state_data = await state.get_data()
        category = await Category.get(id=state_data['category_id'])
        await query.message.edit_text(f"Подтвердите: {state_data['amount']} в категории {category.name}", reply_markup=get_confirmation_keyboard(is_expense=False))

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(income_sum, state=IncomeStates.sum)
    dp.register_callback_query_handler(income_category_callback, state=IncomeStates.category)
    dp.register_message_handler(income_create_category, state=IncomeStates.category, content_types=['text'])
    dp.register_callback_query_handler(income_confirm_callback, state=IncomeStates.confirm)
    dp.register_callback_query_handler(income_edit_callback, state=IncomeStates.edit)