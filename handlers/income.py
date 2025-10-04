from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import dp, bot
from states import AddIncome
from keyboards import get_categories_keyboard, get_wallets_keyboard, get_confirm_keyboard
from database import add_transaction, Category, add_category
from utils import delete_message_safe
import logging
import re

def register_income_handlers(dp):
    @dp.message(lambda message: message.text == '💵 Внести доход')
    async def add_income_start(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        await state.set_state(AddIncome.amount)
        sent = await message.answer("Введите сумму дохода:", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.message(AddIncome.amount)
    async def add_income_amount(message: types.Message, state: FSMContext):
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
            await state.set_state(AddIncome.source)
            keyboard = await get_categories_keyboard('income')
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_inc")])
            sent = await message.answer("Выберите источник:", reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
        except ValueError:
            sent = await message.answer("Пожалуйста, введите числовую сумму.")
            await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.callback_query(lambda c: c.data.startswith('cat_income_'), AddIncome.source)
    async def add_income_source(callback: types.CallbackQuery, state: FSMContext):
        try:
            if not re.match(r'^cat_income_[\w\s-]+$', callback.data):
                raise ValueError("Invalid callback data format")
            source = callback.data.split('_')[2]
            if not await Category.filter(name=source, kind__in=['income', 'both']).exists():
                raise ValueError("Source does not exist")
            await state.update_data(source=source)
            await state.set_state(AddIncome.wallet)
            keyboard = await get_wallets_keyboard()
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_inc")])
            sent = await callback.message.edit_text("Выберите кошелек:", reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка в add_income_source: {e}")
            sent = await callback.message.edit_text("Ошибка при выборе источника. Начните заново.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
            await callback.answer()

    @dp.callback_query(lambda c: c.data == 'add_cat_income', AddIncome.source)
    async def add_income_add_category(callback: types.CallbackQuery, state: FSMContext):
        sent = await callback.message.edit_text("Введите название нового источника:")
        await state.set_state(AddIncome.add_new_cat_inc)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.message(AddIncome.add_new_cat_inc)
    async def add_new_category_income(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        source_name = message.text.strip()
        if not source_name or len(source_name) > 50 or not re.match(r'^[\w\s-]+$', source_name):
            sent = await message.answer("Название источника не может быть пустым, длиннее 50 символов или содержать специальные символы. Попробуйте снова:")
            await state.update_data(last_message_id=sent.message_id)
            await message.delete()
            return
        try:
            if await add_category(source_name, '🆕', 'income'):
                await state.update_data(source=source_name)
                await state.set_state(AddIncome.wallet)
                keyboard = await get_wallets_keyboard()
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_inc")])
                sent = await message.answer("Выберите кошелек:", reply_markup=keyboard)
                await state.update_data(last_message_id=sent.message_id)
            else:
                sent = await message.answer("Источник уже существует или достигнут лимит (50). Попробуйте другое название.")
                await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в add_new_category_income: {e}")
            sent = await message.answer("Ошибка при добавлении источника. Попробуйте снова.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await message.delete()

    @dp.callback_query(lambda c: c.data.startswith('wallet_'), AddIncome.wallet)
    async def add_income_wallet(callback: types.CallbackQuery, state: FSMContext):
        try:
            if not re.match(r'^wallet_[\w\s-]+$', callback.data):
                raise ValueError("Invalid callback data format")
            wallet = callback.data.split('_')[1]
            if not await Wallet.filter(name=wallet).exists():
                raise ValueError("Wallet does not exist")
            await state.update_data(wallet=wallet)
            await state.set_state(AddIncome.confirm)
            data = await state.get_data()
            if 'source' not in data or 'amount' not in data:
                sent = await callback.message.edit_text("Ошибка: данные неполные. Начните заново.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await state.clear()
                await callback.answer()
                return
            amount = data['amount']
            source = data['source']
            cat_obj = await Category.get_or_none(name=source)
            emoji = cat_obj.emoji if cat_obj else '🆕'
            text = f"✅ {amount:.2f} ₽ | {emoji} {source} | {wallet}"
            keyboard = get_confirm_keyboard('inc')
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_inc")])
            sent = await callback.message.edit_text(text, reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка в add_income_wallet: {e}")
            sent = await callback.message.edit_text("Ошибка при выборе кошелька. Начните заново.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
            await callback.answer()

    @dp.callback_query(lambda c: c.data == 'confirm_inc')
    async def add_income_confirm(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        if 'source' not in data or 'wallet' not in data or 'amount' not in data:
            sent = await callback.message.edit_text("Ошибка: недостающие данные. Начните заново.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
            await callback.answer()
            return
        try:
            await add_transaction('income', data['amount'], data['source'], data['wallet'])
            sent = await callback.message.edit_text("✅ Доход сохранен!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_main")]
            ]))
            await state.update_data(last_message_id=sent.message_id)
            await asyncio.sleep(3)
            await delete_message_safe(bot, callback.message.chat.id, sent.message_id)
            await state.clear()
            sent = await bot.send_message(callback.message.chat.id, "💼 Ты в своём кошельке", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в add_income_confirm: {e}")
            sent = await callback.message.edit_text("Ошибка при сохранении дохода. Попробуйте снова.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'change_inc')
    async def add_income_change(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        await state.set_state(AddIncome.amount)
        sent = await callback.message.edit_text("Введите сумму дохода:")
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'back_inc')
    async def add_income_back(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        await state.clear()
        sent = await callback.message.edit_text("💼 Ты в своём кошельке", reply_markup=get_main_menu())
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()