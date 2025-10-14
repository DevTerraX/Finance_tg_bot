# handlers/expense.py
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from ..utils.db_utils import get_or_create_user, get_categories, create_category, create_transaction
from ..utils.validation import validate_amount
from ..utils.cleanup import clean_chat
from ..keyboards.category import get_categories_keyboard
from ..keyboards.confirmation import get_confirmation_keyboard, get_edit_keyboard
from ..states.expense_states import ExpenseStates

async def expense_sum(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    try:
        amount = validate_amount(message.text)
        await state.update_data(amount=amount)
        await ExpenseStates.category.set()
        categories = await get_categories(user, 'expense')
        keyboard = get_categories_keyboard(categories)
        await message.answer("Выберите категорию:", reply_markup=keyboard)
    except ValueError as e:
        await message.answer(str(e) + " Попробуйте снова.")

async def expense_category_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    if data.startswith('select_category_'):
        cat_id = int(data.split('_')[-1])
        await state.update_data(category_id=cat_id)
        await ExpenseStates.confirm.set()
        state_data = await state.get_data()
        amount = state_data['amount']
        category = (await get_categories(await get_or_create_user(query.from_user.id), 'expense'))[0]  # Найти по id
        await query.message.edit_text(f"Подтвердите: {amount} в категории {category.name}", reply_markup=get_confirmation_keyboard())
    elif data == 'create_category':
        await ExpenseStates.category.set()  # Остаёмся, но просим текст
        await query.message.edit_text("Введите название новой категории:")
    elif data == 'back':
        await state.finish()
        from .menu import get_main_menu
        await query.message.edit_text("Главное меню", reply_markup=get_main_menu())

async def expense_create_category(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    name = message.text.strip()
    category = await create_category(user, name, 'expense')
    await state.update_data(category_id=category.id)
    await ExpenseStates.confirm.set()
    state_data = await state.get_data()
    await message.answer(f"Категория создана. Подтвердите: {state_data['amount']} в {name}", reply_markup=get_confirmation_keyboard())

async def expense_confirm_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    user = await get_or_create_user(query.from_user.id)
    state_data = await state.get_data()
    if data == 'confirm':
        await create_transaction(user, state_data['amount'], state_data['category_id'], 'expense', state_data.get('check'))
        await query.message.edit_text("Расход добавлен!")
        await state.finish()
        if user.clean_chat:
            await clean_chat(query.bot, query.message.chat.id, query.message.message_id)
    elif data == 'edit':
        await ExpenseStates.edit.set()
        await query.message.edit_text("Что редактировать?", reply_markup=get_edit_keyboard())
    elif data == 'add_check':
        await ExpenseStates.check.set()
        await query.message.edit_text("Отправьте чек (текст или фото):")
    elif data == 'back':
        await ExpenseStates.category.set()
        categories = await get_categories(user, 'expense')
        await query.message.edit_text("Выберите категорию:", reply_markup=get_categories_keyboard(categories))

async def expense_edit_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    if data == 'edit_sum':
        await ExpenseStates.sum.set()
        await query.message.edit_text("Введите новую сумму:")
    elif data == 'edit_category':
        await ExpenseStates.category.set()
        user = await get_or_create_user(query.from_user.id)
        categories = await get_categories(user, 'expense')
        await query.message.edit_text("Выберите новую категорию:", reply_markup=get_categories_keyboard(categories))
    elif data == 'back':
        await ExpenseStates.confirm.set()
        state_data = await state.get_data()
        # Повторить подтверждение

async def expense_check(message: types.Message, state: FSMContext):
    check = message.text or (message.photo[-1].file_id if message.photo else None)  # Текст или file_id фото
    await state.update_data(check=check)
    await ExpenseStates.confirm.set()
    await message.answer("Чек добавлен. Подтвердите.", reply_markup=get_confirmation_keyboard())

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(expense_sum, state=ExpenseStates.sum)
    dp.register_callback_query_handler(expense_category_callback, state=ExpenseStates.category)
    dp.register_message_handler(expense_create_category, state=ExpenseStates.category)  # Для текста новой категории
    dp.register_callback_query_handler(expense_confirm_callback, state=ExpenseStates.confirm)
    dp.register_callback_query_handler(expense_edit_callback, state=ExpenseStates.edit)
    dp.register_message_handler(expense_check, state=ExpenseStates.check, content_types=['text', 'photo'])