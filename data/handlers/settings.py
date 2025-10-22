from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from ..utils.db_utils import (
    get_or_create_user,
    get_categories,
    create_category,
    delete_category
)
from ..utils.cleanup import clean_chat
from ..keyboards.main_menu import get_main_menu, BACK_BUTTON, SETTINGS_BUTTON
from ..keyboards.category import get_categories_keyboard
from ..keyboards.settings import (
    get_settings_keyboard,
    get_profile_keyboard,
    get_notifications_keyboard,
    get_category_management_keyboard,
    get_cancel_keyboard,
    PROFILE_BUTTON,
    EXPENSE_CATEGORIES_BUTTON,
    INCOME_CATEGORIES_BUTTON,
    NOTIFICATIONS_BUTTON,
    AUTO_CLEAN_PREFIX,
    CATEGORY_ADD_BUTTON,
    CATEGORY_DELETE_BUTTON,
    CANCEL_BUTTON
)
from ..states.settings_states import SettingsStates


async def open_settings(message: types.Message, state: FSMContext):
    await state.finish()
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await SettingsStates.root.set()
    await message.answer("⚙️ Настройки: выбери, что настроить.", reply_markup=get_settings_keyboard())


async def settings_root_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    text = message.text

    if text == PROFILE_BUTTON:
        await SettingsStates.profile_menu.set()
        await message.answer("👤 Управление профилем:", reply_markup=get_profile_keyboard(user))
    elif text == EXPENSE_CATEGORIES_BUTTON:
        await SettingsStates.categories_menu.set()
        await state.update_data(category_type='expense')
        await message.answer("📂 Категории расходов:", reply_markup=get_category_management_keyboard())
    elif text == INCOME_CATEGORIES_BUTTON:
        await SettingsStates.categories_menu.set()
        await state.update_data(category_type='income')
        await message.answer("💰 Категории доходов:", reply_markup=get_category_management_keyboard())
    elif text == NOTIFICATIONS_BUTTON:
        await SettingsStates.notifications_menu.set()
        await message.answer("🔔 Управление напоминаниями:", reply_markup=get_notifications_keyboard(user))
    elif text == BACK_BUTTON:
        await state.finish()
        reply = await message.answer("🏠 Возвращаю в главное меню.", reply_markup=get_main_menu())
        if user.clean_chat:
            await clean_chat(message.bot, message.chat.id, reply.message_id)
    else:
        await message.answer("Пожалуйста, выбери пункт из списка ниже.", reply_markup=get_settings_keyboard())


async def profile_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    text = message.text

    if text.startswith(AUTO_CLEAN_PREFIX):
        user.clean_chat = not user.clean_chat
        await user.save()
        status = 'включена' if user.clean_chat else 'выключена'
        await message.answer(f"🧹 Автоочистка теперь {status}.", reply_markup=get_profile_keyboard(user))
    elif text == "✏️ Изменить имя":
        await SettingsStates.edit_name.set()
        await message.answer("✏️ Введи новое имя профиля:", reply_markup=get_cancel_keyboard())
    elif text.startswith("💱 Валюта"):
        await SettingsStates.edit_currency.set()
        await message.answer("💱 Укажи символ валюты (например, ₽ или USD):", reply_markup=get_cancel_keyboard())
    elif text.startswith("🌍 Часовой пояс"):
        await SettingsStates.edit_timezone.set()
        await message.answer("🌍 Введи часовой пояс (например, Europe/Moscow):", reply_markup=get_cancel_keyboard())
    elif text.startswith("📅 Формат даты"):
        await SettingsStates.edit_date_format.set()
        await message.answer("📅 Введи формат даты (например, DD.MM.YYYY или YYYY-MM-DD):", reply_markup=get_cancel_keyboard())
    elif text == BACK_BUTTON:
        await SettingsStates.root.set()
        reply = await message.answer("⚙️ Выбери следующий раздел настроек:", reply_markup=get_settings_keyboard())
        if user.clean_chat:
            await clean_chat(message.bot, message.chat.id, reply.message_id)
    else:
        await message.answer("Пожалуйста, выбери действие из меню ниже.", reply_markup=get_profile_keyboard(user))


async def profile_edit_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    text = message.text.strip()
    current_state = await state.get_state()

    if text == CANCEL_BUTTON:
        await SettingsStates.profile_menu.set()
        await message.answer("⛔ Изменения отменены.", reply_markup=get_profile_keyboard(user))
        return

    if current_state == SettingsStates.edit_name.state:
        if not text:
            await message.answer("⚠️ Имя не может быть пустым. Попробуй снова.", reply_markup=get_cancel_keyboard())
            return
        user.name = text[:100]
        await user.save()
        await SettingsStates.profile_menu.set()
        await message.answer(f"✅ Имя обновлено: {user.name}", reply_markup=get_profile_keyboard(user))
    elif current_state == SettingsStates.edit_currency.state:
        if len(text) > 8:
            await message.answer("⚠️ Символ валюты слишком длинный. Попробуй снова.", reply_markup=get_cancel_keyboard())
            return
        user.currency = text
        await user.save()
        await SettingsStates.profile_menu.set()
        await message.answer(f"✅ Валюта обновлена: {user.currency}", reply_markup=get_profile_keyboard(user))
    elif current_state == SettingsStates.edit_timezone.state:
        try:
            ZoneInfo(text)
        except ZoneInfoNotFoundError:
            await message.answer("⚠️ Часовой пояс не найден. Пример: Europe/Moscow.", reply_markup=get_cancel_keyboard())
            return
        user.timezone = text
        await user.save()
        await SettingsStates.profile_menu.set()
        await message.answer(f"✅ Часовой пояс обновлён: {user.timezone}", reply_markup=get_profile_keyboard(user))
    elif current_state == SettingsStates.edit_date_format.state:
        if not _is_valid_date_format(text):
            await message.answer("⚠️ Некорректный формат. Используй комбинацию DD, MM, YYYY.", reply_markup=get_cancel_keyboard())
            return
        user.date_format = text
        await user.save()
        await SettingsStates.profile_menu.set()
        await message.answer(f"✅ Формат даты обновлён: {user.date_format}", reply_markup=get_profile_keyboard(user))


def _is_valid_date_format(pattern: str) -> bool:
    tokens = {"DD", "MM", "YYYY"}
    return all(token in pattern for token in tokens) and len(pattern) <= 16


async def notifications_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    text = message.text

    if text.startswith("🔔 Напоминания"):
        user.daily_reminder_enabled = not user.daily_reminder_enabled
        if not user.daily_reminder_enabled:
            user.last_reminder_sent = None
        await user.save()
        await message.answer(
            f"🔔 Напоминания {'включены' if user.daily_reminder_enabled else 'выключены'}.",
            reply_markup=get_notifications_keyboard(user)
        )
    elif text.startswith("⏰ Время напоминания"):
        await SettingsStates.edit_reminder_time.set()
        await message.answer("⏰ Введи время в формате ЧЧ:ММ:", reply_markup=get_cancel_keyboard())
    elif text == BACK_BUTTON:
        await SettingsStates.root.set()
        reply = await message.answer("⚙️ Выбери следующий раздел настроек:", reply_markup=get_settings_keyboard())
        if user.clean_chat:
            await clean_chat(message.bot, message.chat.id, reply.message_id)
    else:
        await message.answer("Пожалуйста, выбери действие из меню ниже.", reply_markup=get_notifications_keyboard(user))


async def reminder_time_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    text = message.text.strip()

    if text == CANCEL_BUTTON:
        await SettingsStates.notifications_menu.set()
        await message.answer("⛔ Изменения отменены.", reply_markup=get_notifications_keyboard(user))
        return

    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await message.answer("⚠️ Некорректный формат времени. Используй ЧЧ:ММ.", reply_markup=get_cancel_keyboard())
        return

    user.reminder_time = text
    user.last_reminder_sent = None
    await user.save()
    await SettingsStates.notifications_menu.set()
    await message.answer(f"✅ Время напоминания обновлено: {user.reminder_time}", reply_markup=get_notifications_keyboard(user))


async def categories_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    text = message.text
    state_data = await state.get_data()
    category_type = state_data.get('category_type', 'expense')

    if text == CATEGORY_ADD_BUTTON:
        await SettingsStates.add_category.set()
        await message.answer("🆕 Введи название новой категории:", reply_markup=get_cancel_keyboard())
    elif text == CATEGORY_DELETE_BUTTON:
        categories = await get_categories(user, category_type)
        if not categories:
            await message.answer("⚠️ Нет категорий для удаления.", reply_markup=get_category_management_keyboard())
            return
        keyboard = get_categories_keyboard(categories, type=category_type, for_delete=True)
        await message.answer("🗑️ Выбери категорию для удаления:", reply_markup=keyboard)
        await SettingsStates.delete_category.set()
    elif text == BACK_BUTTON:
        await SettingsStates.root.set()
        reply = await message.answer("⚙️ Выбери следующий раздел настроек:", reply_markup=get_settings_keyboard())
        if user.clean_chat:
            await clean_chat(message.bot, message.chat.id, reply.message_id)
    else:
        await message.answer("Используй кнопки меню, чтобы управлять категориями.", reply_markup=get_category_management_keyboard())


async def add_category_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if text == CANCEL_BUTTON:
        await SettingsStates.categories_menu.set()
        await message.answer("⛔ Добавление отменено.", reply_markup=get_category_management_keyboard())
        return

    if not text:
        await message.answer("⚠️ Название не может быть пустым. Попробуй снова.", reply_markup=get_cancel_keyboard())
        return

    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    state_data = await state.get_data()
    category_type = state_data.get('category_type', 'expense')
    await create_category(user, text, category_type)
    await SettingsStates.categories_menu.set()
    await message.answer(f"✅ Категория '{text}' добавлена.", reply_markup=get_category_management_keyboard())


async def delete_category_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    state_data = await state.get_data()
    category_type = state_data.get('category_type', 'expense')

    if data.startswith('delete_category_'):
        cat_id = int(data.split('_')[-1])
        await delete_category(cat_id)
        await query.answer("Категория удалена.")
        categories = await get_categories(user, category_type)
        if categories:
            keyboard = get_categories_keyboard(categories, type=category_type, for_delete=True)
            await query.message.edit_text("🗑️ Категория удалена. Выбери следующую:", reply_markup=keyboard)
        else:
            await SettingsStates.categories_menu.set()
            await query.message.edit_text("🗃️ Все категории удалены.", reply_markup=None)
            await query.message.answer("📂 Меню категорий:", reply_markup=get_category_management_keyboard())
    elif data == 'back':
        await SettingsStates.categories_menu.set()
        await query.message.delete()
        await query.message.answer("📂 Меню категорий:", reply_markup=get_category_management_keyboard())


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(open_settings, lambda m: m.text == SETTINGS_BUTTON, state="*")
    dp.register_message_handler(settings_root_handler, state=SettingsStates.root)
    dp.register_message_handler(profile_handler, state=SettingsStates.profile_menu)
    dp.register_message_handler(profile_edit_handler, state=[
        SettingsStates.edit_name,
        SettingsStates.edit_currency,
        SettingsStates.edit_timezone,
        SettingsStates.edit_date_format
    ])
    dp.register_message_handler(notifications_handler, state=SettingsStates.notifications_menu)
    dp.register_message_handler(reminder_time_handler, state=SettingsStates.edit_reminder_time)
    dp.register_message_handler(categories_handler, state=SettingsStates.categories_menu)
    dp.register_message_handler(add_category_handler, state=SettingsStates.add_category)
    dp.register_callback_query_handler(delete_category_callback, state=SettingsStates.delete_category)
