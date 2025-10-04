from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import dp, bot
from database import add_transaction, Category, Wallet
from keyboards import get_main_menu
from utils import delete_message_safe
import logging
import re
import asyncio

def register_quick_handlers(dp):
    @dp.message(commands=['e'])
    async def quick_expense(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        parts = message.text.split(maxsplit=3)  # Разделяем на команду и до 3 аргументов
        if len(parts) < 4:
            sent = await message.answer("Неверный формат. Пример: /e 500 еда наличные", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await message.delete()
            return
        try:
            amount = float(parts[1])
            if amount <= 0:
                sent = await message.answer("Сумма должна быть положительной.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            category = parts[2].strip()
            wallet = parts[3].strip()
            if not re.match(r'^[\w\s-]+$', category) or len(category) > 50:
                sent = await message.answer("Недопустимое имя категории (только буквы, цифры, пробелы, дефисы, до 50 символов).", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            if not re.match(r'^[\w\s-]+$', wallet) or len(wallet) > 50:
                sent = await message.answer("Недопустимое имя кошелька (только буквы, цифры, пробелы, дефисы, до 50 символов).", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            cat_exists = await Category.filter(name=category, kind__in=['expense', 'both']).exists()
            if not cat_exists:
                sent = await message.answer(f"Категория '{category}' не найдена.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            wallet_exists = await Wallet.filter(name=wallet).exists()
            if not wallet_exists:
                sent = await message.answer(f"Кошелек '{wallet}' не найден.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            await add_transaction('expense', amount, category, wallet)
            logging.info(f"Quick expense added: amount={amount}, category={category}, wallet={wallet}, chat_id={message.chat.id}")
            sent = await message.answer("✅ Расход сохранен быстро!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_main")]
            ]))
            await state.update_data(last_message_id=sent.message_id)
            await asyncio.sleep(3)
            await delete_message_safe(bot, message.chat.id, sent.message_id)
            sent = await message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        except ValueError:
            sent = await message.answer("Неверный формат суммы. Пример: /e 500 еда наличные", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в quick_expense: {e}")
            sent = await message.answer("Ошибка при сохранении расхода. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.message(commands=['i'])
    async def quick_income(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        parts = message.text.split(maxsplit=3)  # Разделяем на команду и до 3 аргументов
        if len(parts) < 4:
            sent = await message.answer("Неверный формат. Пример: /i 1000 зарплата карта", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await message.delete()
            return
        try:
            amount = float(parts[1])
            if amount <= 0:
                sent = await message.answer("Сумма должна быть положительной.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            source = parts[2].strip()
            wallet = parts[3].strip()
            if not re.match(r'^[\w\s-]+$', source) or len(source) > 50:
                sent = await message.answer("Недопустимое имя источника (только буквы, цифры, пробелы, дефисы, до 50 символов).", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            if not re.match(r'^[\w\s-]+$', wallet) or len(wallet) > 50:
                sent = await message.answer("Недопустимое имя кошелька (только буквы, цифры, пробелы, дефисы, до 50 символов).", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            source_exists = await Category.filter(name=source, kind__in=['income', 'both']).exists()
            if not source_exists:
                sent = await message.answer(f"Источник '{source}' не найден.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            wallet_exists = await Wallet.filter(name=wallet).exists()
            if not wallet_exists:
                sent = await message.answer(f"Кошелек '{wallet}' не найден.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await message.delete()
                return
            await add_transaction('income', amount, source, wallet)
            logging.info(f"Quick income added: amount={amount}, source={source}, wallet={wallet}, chat_id={message.chat.id}")
            sent = await message.answer("✅ Доход сохранен быстро!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_main")]
            ]))
            await state.update_data(last_message_id=sent.message_id)
            await asyncio.sleep(3)
            await delete_message_safe(bot, message.chat.id, sent.message_id)
            sent = await message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        except ValueError:
            sent = await message.answer("Неверный формат суммы. Пример: /i 1000 зарплата карта", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в quick_income: {e}")
            sent = await message.answer("Ошибка при сохранении дохода. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        await message.delete()