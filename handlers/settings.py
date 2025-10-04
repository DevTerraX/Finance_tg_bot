from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from bot import dp, bot
from states import Settings, PinCheck
from keyboards import get_settings_keyboard, get_wallets_keyboard, get_categories_keyboard, get_manage_keyboard
from database import get_pin, set_pin, add_wallet, delete_wallet, add_category, delete_category, set_reminder_time, add_goal, get_goals, Wallet, Category, Settings
from utils import delete_message_safe
import logging
import re

def register_settings_handlers(dp):
    @dp.message(lambda message: message.text == '⚙ Настройки')
    async def settings(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        try:
            pin = await get_pin()
            if pin:
                await state.set_state(PinCheck.pin)
                sent = await message.answer("Введите PIN для доступа к настройкам:")
                await state.update_data(last_message_id=sent.message_id)
            else:
                sent = await message.answer("Выберите опцию настроек:", reply_markup=get_settings_keyboard())
                await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в settings: {e}")
            sent = await message.answer("Ошибка при доступе к настройкам. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.message(PinCheck.pin)
    async def check_pin(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        input_pin = message.text.strip()
        try:
            pin = await get_pin()
            if input_pin == pin:
                await state.clear()
                sent = await message.answer("Доступ разрешён. Выберите опцию настроек:", reply_markup=get_settings_keyboard())
                await state.update_data(last_message_id=sent.message_id)
            else:
                sent = await message.answer("Неверный PIN. Попробуйте снова:")
                await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в check_pin: {e}")
            sent = await message.answer("Ошибка при проверке PIN. Попробуйте снова.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await message.delete()

    @dp.callback_query(lambda c: c.data == 'manage_wallets')
    async def manage_wallets(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        keyboard = get_manage_keyboard('wallet')
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_settings")])
        sent = await callback.message.edit_text("Управление кошельками:", reply_markup=keyboard)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'add_wallet')
    async def add_wallet_start(callback: types.CallbackQuery, state: FSMContext):
        sent = await callback.message.edit_text("Введите название нового кошелька:")
        await state.set_state(Settings.wallet_add)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.message(Settings.wallet_add)
    async def add_wallet_finish(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        name = message.text.strip()
        if not name or len(name) > 50 or not re.match(r'^[\w\s-]+$', name):
            sent = await message.answer("Название кошелька не может быть пустым, длиннее 50 символов или содержать специальные символы. Попробуйте снова:")
            await state.update_data(last_message_id=sent.message_id)
            await message.delete()
            return
        try:
            if await add_wallet(name):
                sent = await message.answer("Кошелек добавлен!", reply_markup=get_settings_keyboard())
                await state.update_data(last_message_id=sent.message_id)
                await state.clear()
            else:
                sent = await message.answer("Кошелек уже существует или достигнут лимит (50). Попробуйте другое название.")
                await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в add_wallet_finish: {e}")
            sent = await message.answer("Ошибка при добавлении кошелька. Попробуйте снова.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await message.delete()

    @dp.callback_query(lambda c: c.data == 'delete_wallet')
    async def delete_wallet_start(callback: types.CallbackQuery, state: FSMContext):
        keyboard = await get_wallets_keyboard()
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_settings")])
        sent = await callback.message.edit_text("Выберите кошелек для удаления:", reply_markup=keyboard)
        await state.set_state(Settings.wallet_delete)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data.startswith('wallet_'), Settings.wallet_delete)
    async def delete_wallet_confirm(callback: types.CallbackQuery, state: FSMContext):
        try:
            if not re.match(r'^wallet_[\w\s-]+$', callback.data):
                raise ValueError("Invalid callback data format")
            name = callback.data.split('_')[1]
            if not await Wallet.filter(name=name).exists():
                raise ValueError("Wallet does not exist")
            await state.update_data(wallet_to_delete=name)
            sent = await callback.message.edit_text(f"Вы уверены, что хотите удалить кошелек '{name}'?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_delete_wallet")],
                [InlineKeyboardButton(text="Назад", callback_data="back_settings")]
            ]))
            await state.set_state(Settings.wallet_confirm_delete)
            await state.update_data(last_message_id=sent.message_id)
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка в delete_wallet_confirm: {e}")
            sent = await callback.message.edit_text("Ошибка при выборе кошелька. Начните заново.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()

    @dp.callback_query(lambda c: c.data == 'confirm_delete_wallet', Settings.wallet_confirm_delete)
    async def delete_wallet_finish(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        name = data.get('wallet_to_delete')
        if not name:
            sent = await callback.message.edit_text("Ошибка: кошелек не выбран. Начните заново.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
            await callback.answer()
            return
        try:
            await delete_wallet(name)
            sent = await callback.message.edit_text("Кошелек удален!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_settings")]
            ]))
            await state.update_data(last_message_id=sent.message_id)
            await asyncio.sleep(3)
            await delete_message_safe(bot, callback.message.chat.id, sent.message_id)
            await state.clear()
            sent = await bot.send_message(callback.message.chat.id, "Выберите опцию настроек:", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в delete_wallet_finish: {e}")
            sent = await callback.message.edit_text("Ошибка при удалении кошелька. Попробуйте снова.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'manage_categories')
    async def manage_categories(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Расходы", callback_data="manage_expense_categories")],
            [InlineKeyboardButton(text="Доходы", callback_data="manage_income_categories")],
            [InlineKeyboardButton(text="Назад", callback_data="back_settings")]
        ])
        sent = await callback.message.edit_text("Выберите тип категорий:", reply_markup=keyboard)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'manage_expense_categories')
    async def manage_expense_categories(callback: types.CallbackQuery, state: FSMContext):
        keyboard = get_manage_keyboard('expense_category')
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_settings")])
        sent = await callback.message.edit_text("Управление категориями расходов:", reply_markup=keyboard)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'manage_income_categories')
    async def manage_income_categories(callback: types.CallbackQuery, state: FSMContext):
        keyboard = get_manage_keyboard('income_category')
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_settings")])
        sent = await callback.message.edit_text("Управление категориями доходов:", reply_markup=keyboard)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'add_expense_category')
    async def add_expense_category_start(callback: types.CallbackQuery, state: FSMContext):
        sent = await callback.message.edit_text("Введите название новой категории расходов:")
        await state.set_state(Settings.category_add)
        await state.update_data(category_kind='expense')
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'add_income_category')
    async def add_income_category_start(callback: types.CallbackQuery, state: FSMContext):
        sent = await callback.message.edit_text("Введите название новой категории доходов:")
        await state.set_state(Settings.category_add)
        await state.update_data(category_kind='income')
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.message(Settings.category_add)
    async def add_category_finish(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        name = message.text.strip()
        data = await state.get_data()
        kind = data.get('category_kind', 'both')
        if kind not in ['expense', 'income', 'both']:
            sent = await message.answer("Ошибка: неверный тип категории. Начните заново.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
            await message.delete()
            return
        if not name or len(name) > 50 or not re.match(r'^[\w\s-]+$', name):
            sent = await message.answer("Название категории не может быть пустым, длиннее 50 символов или содержать специальные символы. Попробуйте снова:")
            await state.update_data(last_message_id=sent.message_id)
            await message.delete()
            return
        try:
            if await add_category(name, '🆕', kind):
                sent = await message.answer("Категория добавлена!", reply_markup=get_settings_keyboard())
                await state.update_data(last_message_id=sent.message_id)
                await state.clear()
            else:
                sent = await message.answer("Категория уже существует или достигнут лимит (50). Попробуйте другое название.")
                await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в add_category_finish: {e}")
            sent = await message.answer("Ошибка при добавлении категории. Попробуйте снова.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await message.delete()

    @dp.callback_query(lambda c: c.data == 'delete_expense_category')
    async def delete_expense_category_start(callback: types.CallbackQuery, state: FSMContext):
        keyboard = await get_categories_keyboard('expense')
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_settings")])
        sent = await callback.message.edit_text("Выберите категорию расходов для удаления:", reply_markup=keyboard)
        await state.set_state(Settings.category_delete)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'delete_income_category')
    async def delete_income_category_start(callback: types.CallbackQuery, state: FSMContext):
        keyboard = await get_categories_keyboard('income')
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_settings")])
        sent = await callback.message.edit_text("Выберите категорию доходов для удаления:", reply_markup=keyboard)
        await state.set_state(Settings.category_delete)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data.startswith('cat_'), Settings.category_delete)
    async def delete_category_confirm(callback: types.CallbackQuery, state: FSMContext):
        try:
            if not re.match(r'^cat_(expense|income)_[\w\s-]+$', callback.data):
                raise ValueError("Invalid callback data format")
            name = callback.data.split('_')[2]
            kind = callback.data.split('_')[1]
            if not await Category.filter(name=name, kind__in=[kind, 'both']).exists():
                raise ValueError("Category does not exist")
            await state.update_data(category_to_delete=name)
            sent = await callback.message.edit_text(f"Вы уверены, что хотите удалить категорию '{name}'?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_delete_category")],
                [InlineKeyboardButton(text="Назад", callback_data="back_settings")]
            ]))
            await state.set_state(Settings.category_confirm_delete)
            await state.update_data(last_message_id=sent.message_id)
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка в delete_category_confirm: {e}")
            sent = await callback.message.edit_text("Ошибка при выборе категории. Начните заново.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()

    @dp.callback_query(lambda c: c.data == 'confirm_delete_category', Settings.category_confirm_delete)
    async def delete_category_finish(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        name = data.get('category_to_delete')
        if not name:
            sent = await callback.message.edit_text("Ошибка: категория не выбрана. Начните заново.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
            await callback.answer()
            return
        try:
            await delete_category(name)
            sent = await callback.message.edit_text("Категория удалена!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_settings")]
            ]))
            await state.update_data(last_message_id=sent.message_id)
            await asyncio.sleep(3)
            await delete_message_safe(bot, callback.message.chat.id, sent.message_id)
            await state.clear()
            sent = await bot.send_message(callback.message.chat.id, "Выберите опцию настроек:", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в delete_category_finish: {e}")
            sent = await callback.message.edit_text("Ошибка при удалении категории. Попробуйте снова.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'back_settings')
    async def back_settings(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        await state.clear()
        sent = await callback.message.edit_text("Выберите опцию настроек:", reply_markup=get_settings_keyboard())
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'manage_goals')
    async def manage_goals(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        try:
            goals = await get_goals()
            text = "Текущие цели:\n"
            if not goals:
                text += "- Нет целей\n"
            for goal in goals:
                text += f"{goal[1]}: {goal[3]:.2f}/{goal[2]:.2f} ₽ (текущий: {goal[3]:.2f})\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Добавить цель", callback_data="add_goal")],
                [InlineKeyboardButton(text="Назад", callback_data="back_settings")]
            ])
            sent = await callback.message.edit_text(text, reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в manage_goals: {e}")
            sent = await callback.message.edit_text("Ошибка при получении целей. Попробуйте снова.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'add_goal')
    async def add_goal_start(callback: types.CallbackQuery, state: FSMContext):
        sent = await callback.message.edit_text("Введите описание цели и целевую сумму (например: Отпуск 100000):")
        await state.set_state(Settings.goal_set)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.message(Settings.goal_set)
    async def add_goal_finish(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        parts = message.text.strip().split()
        if len(parts) < 2:
            sent = await message.answer("Неверный формат. Пример: Отпуск 100000")
            await state.update_data(last_message_id=sent.message_id)
            await message.delete()
            return
        description = ' '.join(parts[:-1])
        if len(description) > 100:
            sent = await message.answer("Описание цели не может быть длиннее 100 символов. Попробуйте снова:")
            await state.update_data(last_message_id=sent.message_id)
            await message.delete()
            return
        try:
            target = float(parts[-1])
            if target <= 0:
                sent = await message.answer("Целевая сумма должна быть положительной. Попробуйте снова:")
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            await add_goal(description, target)
            sent = await message.answer("Цель добавлена!", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        except ValueError:
            sent = await message.answer("Целевая сумма должна быть числом.")
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в add_goal_finish: {e}")
            sent = await message.answer("Ошибка при добавлении цели. Попробуйте снова.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await message.delete()

    @dp.callback_query(lambda c: c.data == 'set_reminder')
    async def set_reminder(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        sent = await callback.message.edit_text("Введите время напоминания (HH:MM):")
        await state.set_state(Settings.reminder_set)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.message(Settings.reminder_set)
    async def set_reminder_finish(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        time_ = message.text.strip()
        try:
            hour, minute = map(int, time_.split(':'))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                sent = await message.answer("Неверный формат времени. Попробуйте HH:MM (например, 22:00).")
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            await set_reminder_time(time_, message.chat.id)
            from database import scheduler
            scheduler.remove_all_jobs()
            from database import setup_reminders
            setup_reminders()
            sent = await message.answer("Время напоминания установлено!", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        except ValueError:
            sent = await message.answer("Неверный формат. Пример: 22:00")
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в set_reminder_finish: {e}")
            sent = await message.answer("Ошибка при установке напоминания. Попробуйте снова.", reply_markup=get_settings_keyboard())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await message.delete()

    @dp.callback_query(lambda c: c.data == 'set_pin')
    async def set_pin_handler(callback: types.CallbackQuer)y