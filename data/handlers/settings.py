# handlers/settings.py
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from ..utils.db_utils import get_categories, create_category, delete_category, get_or_create_user
from keyboards.category import get_categories_keyboard
from states.settings_states import SettingsStates

async def settings_menu(message: types.Message, state: FSMContext):
    # Пока только категории
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Категории расходов", callback_data="categories_expense"),
        types.InlineKeyboardButton("Категории доходов", callback_data="categories_income")
    )
    await message.answer("Настройки категорий:", reply_markup=keyboard)

async def settings_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    user = await get_or_create_user(query.from_user.id)
    if data.startswith('categories_'):
        type = data.split('_')[-1]
        await state.update_data(type=type)
        categories = await get_categories(user, type)
        keyboard = get_categories_keyboard(categories, type, for_delete=True)
        await SettingsStates.delete_category.set()
        await query.message.edit_text(f"Категории {type}:", reply_markup=keyboard)
    elif data.startswith('delete_category_'):
        cat_id = int(data.split('_')[-1])
        await delete_category(cat_id)
        await query.message.edit_text("Категория удалена.")
    elif data == 'create_category':
        await SettingsStates.add_category.set()
        await query.message.edit_text("Введите название новой категории:")
    elif data == 'back':
        await state.finish()
        from .menu import get_main_menu
        await query.message.edit_text("Главное меню", reply_markup=get_main_menu())

async def add_category(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    type = state_data['type']
    user = await get_or_create_user(message.from_user.id)
    await create_category(user, message.text.strip(), type)
    await message.answer("Категория добавлена.")
    await state.finish()

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(settings_menu, state=SettingsStates.categories_menu)
    dp.register_callback_query_handler(settings_callback, state=[SettingsStates.categories_menu, SettingsStates.delete_category])
    dp.register_message_handler(add_category, state=SettingsStates.add_category)