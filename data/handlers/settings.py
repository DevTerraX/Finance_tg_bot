# handlers/settings.py
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from ..utils.db_utils import get_categories, create_category, delete_category, get_or_create_user
from ..keyboards.settings import get_settings_keyboard, get_categories_keyboard
from ..states.settings_states import SettingsStates
from ..keyboards.category import get_categories_management_keyboard, get_categories_delete_keyboard

async def settings_menu(message: types.Message, state: FSMContext):
    keyboard = get_settings_keyboard()
    await message.answer(
        "Настройки категорий:", 
        reply_markup=keyboard
    )
    await SettingsStates.categories_menu.set()

async def process_category_type(message: types.Message, state: FSMContext):
    """Обработка выбора типа категорий"""
    type_mapping = {
        "Категории расходов": "expense",
        "Категории доходов": "income"
    }
    
    category_type = type_mapping.get(message.text)
    if not category_type:
        await message.answer("Выберите корректный тип категорий.")
        return
    
    user = await get_or_create_user(message.from_user.id)
    await state.update_data(type=category_type)
    
    # Показываем категории с кнопками управления
    categories = await get_categories(user, category_type)
    management_keyboard = get_categories_management_keyboard(categories, category_type)
    
    await message.answer(
        f"Категории {category_type}:",
        reply_markup=management_keyboard
    )
    await SettingsStates.category_management.set()

async def manage_category(message: types.Message, state: FSMContext):
    """Обработка команд управления категориями"""
    state_data = await state.get_data()
    category_type = state_data.get('type')
    
    if message.text == "Добавить категорию":
        await SettingsStates.add_category.set()
        await message.answer("Введите название новой категории:")
    elif message.text == "Удалить категорию":
        # Показываем список категорий для удаления
        user = await get_or_create_user(message.from_user.id)
        categories = await get_categories(user, category_type)
        delete_keyboard = get_categories_delete_keyboard(categories, category_type)
        await message.answer(
            "Выберите категорию для удаления:",
            reply_markup=delete_keyboard
        )
        await SettingsStates.delete_category.set()
    elif message.text == "Назад":
        await state.finish()
        from .menu import get_main_menu
        await message.answer("Главное меню", reply_markup=get_main_menu())
    else:
        # Проверяем, является ли текст названием категории для удаления
        user = await get_or_create_user(message.from_user.id)
        categories = await get_categories(user, category_type)
        
        for category in categories:
            if message.text == category['name']:
                await delete_category(category['id'])
                await message.answer(f"Категория '{message.text}' удалена.")
                
                # Показываем обновленный список
                updated_categories = await get_categories(user, category_type)
                management_keyboard = get_categories_management_keyboard(updated_categories, category_type)
                await message.answer(
                    f"Категории {category_type}:",
                    reply_markup=management_keyboard
                )
                return
        
        await message.answer("Категория не найдена.")

async def add_category(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    category_type = state_data['type']
    user = await get_or_create_user(message.from_user.id)
    
    await create_category(user, message.text.strip(), category_type)
    await message.answer("Категория добавлена.")
    
    # Показываем обновленный список категорий
    categories = await get_categories(user, category_type)
    management_keyboard = get_categories_management_keyboard(categories, category_type)
    await message.answer(
        f"Категории {category_type}:",
        reply_markup=management_keyboard
    )
    await state.finish()

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(settings_menu, commands=['settings'], state='*')
    dp.register_message_handler(
        process_category_type, 
        state=SettingsStates.categories_menu,
        content_types=['text']
    )
    dp.register_message_handler(
        manage_category,
        state=[SettingsStates.category_management, SettingsStates.delete_category],
        content_types=['text']
    )
    dp.register_message_handler(add_category, state=SettingsStates.add_category)