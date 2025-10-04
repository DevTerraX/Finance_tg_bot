from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from bot import dp, bot
from database import get_balance, get_summary, get_category_summary, get_wallet_summary, Category, Transaction
from keyboards import get_main_menu, get_summaries_keyboard, get_categories_keyboard, get_wallets_keyboard
from utils import delete_message_safe
import logging
from database import Settings
import asyncio
import pandas as pd
import io
import matplotlib.pyplot as plt

def register_common_handlers(dp):
    @dp.message(commands=['start'])
    async def start(message: types.Message, state: FSMContext):
        try:
            settings = await Settings.get_or_none(id=1)
            if settings:
                settings.chat_id = message.chat.id
                await settings.save()
            else:
                await Settings.create(id=1, chat_id=message.chat.id)
            logging.info(f"User started bot: chat_id={message.chat.id}, user_id={message.from_user.id}")
        except Exception as e:
            logging.error(f"Ошибка базы данных в /start: {e}")
            sent = await message.answer("Ошибка базы данных. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await message.delete()
            return
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        sent = await message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())
        await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.message(commands=['getid'])
    async def get_chat_id(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        sent = await message.answer(f"Ваш chat_id: {message.chat.id}", reply_markup=get_main_menu())
        await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.message(lambda message: message.text == '💰 Баланс')
    async def balance(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        try:
            total_balance = await get_balance()
            text = f"📈 Общий баланс: {total_balance:.2f} ₽"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_main")]
            ])
            sent = await message.answer(text, reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в balance: {e}")
            sent = await message.answer("Ошибка при получении баланса. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.message(lambda message: message.text == '📊 Итоги')
    async def summaries(message: types.Message, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        sent = await message.answer("Выберите период или опцию:", reply_markup=get_summaries_keyboard())
        await state.update_data(last_message_id=sent.message_id)
        await message.delete()

    @dp.callback_query(lambda c: c.data.startswith('summary_'))
    async def show_summary(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        period = callback.data.split('_')[1]
        try:
            expenses, incomes = await get_summary(period)
            total_income = sum(amt for _, amt in incomes) if incomes else 0
            total_expense = sum(amt for _, amt in expenses) if expenses else 0
            balance = total_income - total_expense
            text = f"📊 Итог за {period}:\n────────────────\n💸 Расходы:\n"
            if not expenses:
                text += "- Нет расходов\n"
            for cat, amt in expenses:
                category = await Category.get_or_none(name=cat)
                emoji = category.emoji if category else '🆕'
                text += f"- {emoji} {cat}: {amt:.2f} ₽\n"
            text += "\n💰 Доходы:\n"
            if not incomes:
                text += "- Нет доходов\n"
            for cat, amt in incomes:
                category = await Category.get_or_none(name=cat)
                emoji = category.emoji if category else '🆕'
                text += f"- {emoji} {cat}: {amt:.2f} ₽\n"
            text += f"\n📈 Баланс: {balance:+.2f} ₽"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_summary")]
            ])
            sent = await callback.message.edit_text(text, reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в show_summary: {e}")
            sent = await callback.message.edit_text("Ошибка при получении итогов. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'category_summary')
    async def category_summary(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        keyboard = await get_categories_keyboard('both')
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_summary")])
        sent = await callback.message.edit_text("Выберите категорию:", reply_markup=keyboard)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data.startswith('cat_both_'))
    async def show_category_summary(callback: types.CallbackQuery, state: FSMContext):
        try:
            category = callback.data.split('_')[2]
            data = await get_category_summary(category)
            if not data:
                sent = await callback.message.edit_text("Нет данных для этой категории.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back_summary")]
                ]))
                await state.update_data(last_message_id=sent.message_id)
                await callback.answer()
                return
            text = f"Итог по категории {category}:\n"
            for type_, amt in data:
                text += f"{type_.capitalize()}: {amt:.2f} ₽\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_summary")]
            ])
            sent = await callback.message.edit_text(text, reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка в show_category_summary: {e}")
            sent = await callback.message.edit_text("Ошибка при получении итогов. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()

    @dp.callback_query(lambda c: c.data == 'wallet_summary')
    async def wallet_summary(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        keyboard = await get_wallets_keyboard()
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="Назад", callback_data="back_summary")])
        sent = await callback.message.edit_text("Выберите кошелек:", reply_markup=keyboard)
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data.startswith('wallet_'))
    async def show_wallet_summary(callback: types.CallbackQuery, state: FSMContext):
        try:
            wallet = callback.data.split('_')[1]
            data = await get_wallet_summary(wallet)
            if not data:
                sent = await callback.message.edit_text("Нет данных для этого кошелька.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back_summary")]
                ]))
                await state.update_data(last_message_id=sent.message_id)
                await callback.answer()
                return
            text = f"Итог по кошельку {wallet}:\n"
            for type_, amt in data:
                text += f"{type_.capitalize()}: {amt:.2f} ₽\n"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Назад", callback_data="back_summary")]
            ])
            sent = await callback.message.edit_text(text, reply_markup=keyboard)
            await state.update_data(last_message_id=sent.message_id)
            await callback.answer()
        except Exception as e:
            logging.error(f"Ошибка в show_wallet_summary: {e}")
            sent = await callback.message.edit_text("Ошибка при получении итогов. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
            await state.clear()

    @dp.callback_query(lambda c: c.data == 'export_csv')
    async def export_csv(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        try:
            count = await Transaction.all().count()
            if count > 10000:
                sent = await callback.message.edit_text("Слишком много данных для экспорта. Свяжитесь с администратором.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await callback.answer()
                return
            transactions = await Transaction.all().values('id', 'type', 'amount', 'category', 'wallet', 'note', 'date')
            if not transactions:
                sent = await callback.message.edit_text("Нет данных для экспорта.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back_main")]
                ]))
                await state.update_data(last_message_id=sent.message_id)
                await callback.answer()
                return
            df = pd.DataFrame(transactions)
            with io.BytesIO() as csv_buffer:
                df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                sent = await bot.send_document(
                    callback.message.chat.id,
                    BufferedInputFile(csv_buffer.getvalue(), filename='transactions.csv')
                )
                await state.update_data(last_message_id=sent.message_id)
                await asyncio.sleep(3)
                await delete_message_safe(bot, callback.message.chat.id, sent.message_id)
            sent = await callback.message.edit_text("💼 Ты в своём кошельке", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        except Exception as e:
            logging.error(f"Ошибка в export_csv: {e}")
            sent = await callback.message.edit_text("Ошибка при экспорте данных. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'pie_chart')
    async def pie_chart(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        try:
            data = await Transaction.filter(type='expense').group_by('category').annotate(total=sum('amount')).values('category', 'total')
            if not data or all(item['total'] == 0 for item in data):
                sent = await callback.message.edit_text("Нет данных для диаграммы.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Назад", callback_data="back_main")]
                ]))
                await state.update_data(last_message_id=sent.message_id)
                await callback.answer()
                return
            if len(data) > 20:
                sent = await callback.message.edit_text("Слишком много категорий для диаграммы. Попробуйте другой период.", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
                await callback.answer()
                return
            labels = [item['category'] for item in data]
            sizes = [item['total'] for item in data]
            try:
                fig, ax = plt.subplots()
                ax.pie(sizes, labels=labels, autopct='%1.1f%%')
                ax.axis('equal')
                with io.BytesIO() as buf:
                    plt.savefig(buf, format='png')
                    buf.seek(0)
                    sent = await bot.send_photo(
                        callback.message.chat.id,
                        BufferedInputFile(buf.getvalue(), filename='chart.png')
                    )
                    await state.update_data(last_message_id=sent.message_id)
                    await asyncio.sleep(3)
                    await delete_message_safe(bot, callback.message.chat.id, sent.message_id)
                sent = await callback.message.edit_text("💼 Ты в своём кошельке", reply_markup=get_main_menu())
                await state.update_data(last_message_id=sent.message_id)
            finally:
                plt.close()
        except Exception as e:
            logging.error(f"Ошибка в pie_chart: {e}")
            sent = await callback.message.edit_text("Ошибка при создании диаграммы. Попробуйте позже.", reply_markup=get_main_menu())
            await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'back_summary')
    async def back_summary(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        sent = await callback.message.edit_text("Выберите период или опцию:", reply_markup=get_summaries_keyboard())
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'back_main')
    async def back_to_main_callback(callback: types.CallbackQuery, state: FSMContext):
        last_msg_id = (await state.get_data()).get('last_message_id')
        if last_msg_id:
            await delete_message_safe(bot, callback.message.chat.id, last_msg_id)
        await state.update_data(last_message_id=None)
        await state.clear()
        sent = await callback.message.edit_text("💼 Ты в своём кошельке", reply_markup=get_main_menu())
        await state.update_data(last_message_id=sent.message_id)
        await callback.answer()