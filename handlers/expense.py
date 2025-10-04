from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import dp, bot
from states import AddExpense
import asyncio
from database import Wallet
from keyboards import get_categories_keyboard, get_wallets_keyboard, get_confirm_keyboard, get_main_menu
from database import add_transaction, Category, add_category
from utils import delete_message_safe
import logging
import re

def register_expense_handlers(dp):
    @dp.message(lambda message: message.text == '💸 Внести расход')
    async def add_expense_start(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        await state.set_state(AddExpense.amount)
        sent = await message.answer("Введите сумму расхода:", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.message(AddExpense.amount)
    async def add_expense_amount(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        try:
            amount = float(message.text)
            if amount <= 0:
                sent = await message.answer("Сумма должна быть положительной. Попробуйте снова:")
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            await state.update_data(amount=amount)
            await state.set_state(AddExpense.category)
            keyboard = await get_categories_keyboard('expense')
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_exp")])
            sent = await message.answer("Выберите категорию:", reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
        except ValueError:
            sent = await message.answer("Пожалуйста, введите числовую сумму.")
            await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.callback_query(lambda c: c.data.startswith('cat_expense_'), AddExpense.category)
    async def add_expense_category(callback: types.CallbackQuery, state: FSMContext):
        try:
            if not re.match(r'^cat_expense_[\w\s-]+$', callback.data):
                raise ValueError("Invalid callback data format")
            category = callback.data.split('_')[2]
            if not await Category.filter(name=category, kind__in=['expense', 'both']).exists():
                raise ValueError("Category does not exist")
            await state.update_data(category=category)
            await state.set_state(AddExpense.wallet)
            keyboard = await get_wallets_keyboard()
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_exp")])
            sent = await callback.message.edit_text("Выберите кошелек:", reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка в add_expense_category: {e}")
            sent = await callback.message.edit_text("Ошибка при выборе категории. Начните заново.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
            await callback.answer()

    @dp.callback_query(lambda c: c.data == 'add_cat_expense', AddExpense.category)
    async def add_expense_add_category(callback: types.CallbackQuery, state: FSMContext):
        sent = await callback.message.edit_text("Введите название новой категории:")
        await state.set_state(AddExpense.add_new_cat_exp)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.message(AddExpense.add_new_cat_exp)
    async def add_new_category_expense(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        category_name = message.text.strip()
        if not category_name or len(category_name) > 50 or not re.match(r'^[\w\s-]+$', category_name):
            sent = await message.answer("Название категории не может быть пустым, длиннее 50 символов или содержать специальные символы. Попробуйте снова:")
            await state.update_data(last_message_id=sent.message_id)
            await message.delete()
            return
        try:
            if await add_category(category_name, '🆕', 'expense'):
                await state.update_data(category=category_name)
                await state.set_state(AddExpense.wallet)
                keyboard = await get_wallets_keyboard()
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_exp")])
                sent = await message.answer("Выберите кошелек:", reply_markup=keyboard)
                await state.update_data(last_message_id=sent.message_id)
            else:
                sent = await message.answer("Категория уже существует или достигнут лимит (50). Попробуйте другое название.")
                await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в add_new_category_expense: {e}")
            sent = await message.answer("Ошибка при добавлении категории. Попробуйте снова.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await message.delete()

    @dp.callback_query(lambda c: c.data.startswith('wallet_'), AddExpense.wallet)
    async def add_expense_wallet(callback: types.CallbackQuery, state: FSMContext):
        try:
            if not re.match(r'^wallet_[\w\s-]+$', callback.data):
                raise ValueError("Invalid callback data format")
            wallet = callback.data.split('_')[1]
            if not await Wallet.filter(name=wallet).exists():
                raise ValueError("Wallet does not exist")
            await state.update_data(wallet=wallet)
            await state.set_state(AddExpense.confirm)
            data = await state.get_data()
            if 'category' not in data or 'amount' not in data:
                sent = await callback.message.edit_text("Ошибка: данные неполные. Начните заново.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await state.clear()
                await callback.answer()
                return
            amount = data['amount']
            category = data['category']
            cat_obj = await Category.get_or_none(name=category)
            emoji = cat_obj.emoji if cat_obj else '🆕'
            text = f"✅ {amount:.2f} ₽ | {emoji} {category} | {wallet}"
            keyboard = get_confirm_keyboard('exp')
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_exp")])
            sent = await callback.message.edit_text(text, reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка в add_expense_wallet: {e}")
            sent = await callback.message.edit_text("Ошибка при выборе кошелька. Начните заново.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
            await callback.answer()

    @dp.callback_query(lambda c: c.data == 'confirm_exp')
    async def add_expense_confirm(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        if 'category' not in data or 'wallet' not in data or 'amount' not in data:
            sent = await callback.message.edit_text("Ошибка: недостающие данные. Начните заново.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
            await callback.answer()
            return
        try:
            await add_transaction('expense', data['amount'], data['category'], data['wallet'])
            sent = await callback.message.edit_text("✅ Расход сохранен!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_main")]
            ]))
            await state.update_data(last_message_id=sent.message_id)
            await asyncio.sleep(3)
            await delete_message_safe(bot, callback.message.chat.id, sent.message_id)
            await state.clear()
            sent = await bot.send_message(callback.message.chat.id, "💼 Ты в своём кошельке", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в add_expense_confirm: {e}")
            sent = await callback.message.edit_text("Ошибка при сохранении расхода. Попробуйте снова.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'change_exp')
    async def add_expense_change(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        await state.set_state(AddExpense.amount)
        sent = await callback.message.edit_text("Введите сумму расхода:")
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'back_exp')
    async def add_expense_back(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        await state.clear()
        sent = await callback.message.edit_text("💼 Ты в своём кошельке", reply_markup=get_main_menu())
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()