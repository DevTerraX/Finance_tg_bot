import asyncio
import datetime
import io
import logging
import pandas as pd
import matplotlib.pyplot as plt
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import conn, cursor, init_db, add_transaction, get_balance, get_summary, get_category_summary, get_wallet_summary, add_wallet, delete_wallet, add_category, delete_category, set_reminder_time, set_pin, get_pin, add_goal, get_goals
from states import AddExpense, AddIncome, Settings, PinCheck
from keyboards import get_main_menu, get_summaries_keyboard, get_settings_keyboard, get_categories_keyboard, get_wallets_keyboard, get_confirm_keyboard, get_manage_keyboard
from bot import bot

logging.basicConfig(level=logging.INFO)

scheduler = AsyncIOScheduler()

async def send_reminder(chat_id):
    await bot.send_message(chat_id, "Не забудь внести расходы!", reply_markup=get_main_menu())

def setup_reminders():
    cursor.execute("SELECT reminder_time, chat_id FROM settings WHERE id=1")
    result = cursor.fetchone()
    if result and result[1]:
        reminder_time, chat_id = result
        try:
            hour, minute = map(int, reminder_time.split(':'))
            scheduler.add_job(send_reminder, 'cron', hour=hour, minute=minute, args=(chat_id,))
        except ValueError:
            logging.error("Неверный формат времени напоминания")

def register_handlers(dp):
    @dp.message(Command('start'))
    async def start(message: types.Message):
        cursor.execute("UPDATE settings SET chat_id=? WHERE id=1", (message.chat.id,))
        conn.commit()
        await message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())
        scheduler.start()
        setup_reminders()

    @dp.message(Command('getid'))
    async def get_chat_id(message: types.Message):
        await message.answer(f"Ваш chat_id: {message.chat.id}")

    @dp.message(lambda message: message.text == '💰 Баланс')
    async def balance(message: types.Message):
        total_balance = get_balance()
        await message.answer(f"📈 Общий баланс: {total_balance} ₽", reply_markup=get_main_menu())

    @dp.message(lambda message: message.text == '💸 Внести расход')
    async def add_expense_start(message: types.Message, state: FSMContext):
        await state.set_state(AddExpense.amount)
        await message.answer("Введите сумму расхода:", reply_markup=types.ReplyKeyboardRemove())

    @dp.message(AddExpense.amount)
    async def add_expense_amount(message: types.Message, state: FSMContext):
        try:
            amount = float(message.text)
            await state.update_data(amount=amount)
            await state.set_state(AddExpense.category)
            keyboard = get_categories_keyboard('expense')
            await message.answer("Выберите категорию:", reply_markup=keyboard)
        except ValueError:
            await message.answer("Пожалуйста, введите числовую сумму.")

    @dp.callback_query(lambda c: c.data.startswith('cat_expense_'), StateFilter(AddExpense.category))
    async def add_expense_category(callback: types.CallbackQuery, state: FSMContext):
        category = callback.data.split('_')[2]  # Извлекаем имя категории (например, "Еда")
        await state.update_data(category=category)
        await state.set_state(AddExpense.wallet)
        keyboard = get_wallets_keyboard()
        await callback.message.edit_text("Выберите кошелек:", reply_markup=keyboard)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'add_cat_expense', StateFilter(AddExpense.category))
    async def add_expense_add_category(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_text("Введите название новой категории:")
        await state.set_state(AddExpense.add_new_cat_exp)
        await callback.answer()

    @dp.message(StateFilter(AddExpense.add_new_cat_exp))
    async def add_new_category_expense(message: types.Message, state: FSMContext):
        category_name = message.text.strip()
        if not category_name:
            await message.answer("Название категории не может быть пустым. Попробуйте снова:")
            return
        if add_category(category_name, '🆕', 'expense'):
            await state.update_data(category=category_name)
            await state.set_state(AddExpense.wallet)
            keyboard = get_wallets_keyboard()
            await message.answer("Выберите кошелек:", reply_markup=keyboard)
        else:
            await message.answer("Категория уже существует. Попробуйте другое название.")

    @dp.callback_query(lambda c: c.data.startswith('wallet_'), StateFilter(AddExpense.wallet))
    async def add_expense_wallet(callback: types.CallbackQuery, state: FSMContext):
        wallet = callback.data.split('_')[1]
        await state.update_data(wallet=wallet)
        await state.set_state(AddExpense.confirm)
        data = await state.get_data()
        amount = data['amount']
        category = data['category']
        cursor.execute("SELECT emoji FROM categories WHERE name=?", (category,))
        emoji_result = cursor.fetchone()
        emoji = emoji_result[0] if emoji_result else '🆕'
        text = f"✅ {amount} ₽ | {emoji} {category} | {wallet}"
        keyboard = get_confirm_keyboard('exp')
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'confirm_exp')
    async def add_expense_confirm(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        add_transaction('expense', data['amount'], data['category'], data['wallet'])
        await callback.message.edit_text("✅ Расход сохранен!")
        await asyncio.sleep(3)
        await callback.message.delete()
        await state.clear()
        await callback.message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())

    @dp.callback_query(lambda c: c.data == 'change_exp')
    async def add_expense_change(callback: types.CallbackQuery, state: FSMContext):
        await state.set_state(AddExpense.amount)
        await callback.message.edit_text("Введите сумму расхода:")
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'back_exp')
    async def add_expense_back(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())
        await callback.answer()

    # Аналогично для доходов (для краткости, код аналогичен расходам, с заменой 'expense' на 'income', 'category' на 'source')
    @dp.message(lambda message: message.text == '💵 Внести доход')
    async def add_income_start(message: types.Message, state: FSMContext):
        await state.set_state(AddIncome.amount)
        await message.answer("Введите сумму дохода:", reply_markup=types.ReplyKeyboardRemove())

    @dp.message(AddIncome.amount)
    async def add_income_amount(message: types.Message, state: FSMContext):
        try:
            amount = float(message.text)
            await state.update_data(amount=amount)
            await state.set_state(AddIncome.source)
            keyboard = get_categories_keyboard('income')
            await message.answer("Выберите источник:", reply_markup=keyboard)
        except ValueError:
            await message.answer("Пожалуйста, введите числовую сумму.")

    @dp.callback_query(lambda c: c.data.startswith('cat_income_'), StateFilter(AddIncome.source))
    async def add_income_source(callback: types.CallbackQuery, state: FSMContext):
        source = callback.data.split('_')[2]
        await state.update_data(source=source)
        await state.set_state(AddIncome.wallet)
        keyboard = get_wallets_keyboard()
        await callback.message.edit_text("Выберите кошелек:", reply_markup=keyboard)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'add_cat_income', StateFilter(AddIncome.source))
    async def add_income_add_category(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_text("Введите название нового источника:")
        await state.set_state(AddIncome.add_new_cat_inc)
        await callback.answer()

    @dp.message(StateFilter(AddIncome.add_new_cat_inc))
    async def add_new_category_income(message: types.Message, state: FSMContext):
        source_name = message.text.strip()
        if not source_name:
            await message.answer("Название источника не может быть пустым. Попробуйте снова:")
            return
        if add_category(source_name, '🆕', 'income'):
            await state.update_data(source=source_name)
            await state.set_state(AddIncome.wallet)
            keyboard = get_wallets_keyboard()
            await message.answer("Выберите кошелек:", reply_markup=keyboard)
        else:
            await message.answer("Источник уже существует. Попробуйте другое название.")

    @dp.callback_query(lambda c: c.data.startswith('wallet_'), StateFilter(AddIncome.wallet))
    async def add_income_wallet(callback: types.CallbackQuery, state: FSMContext):
        wallet = callback.data.split('_')[1]
        await state.update_data(wallet=wallet)
        await state.set_state(AddIncome.confirm)
        data = await state.get_data()
        amount = data['amount']
        source = data['source']
        cursor.execute("SELECT emoji FROM categories WHERE name=?", (source,))
        emoji_result = cursor.fetchone()
        emoji = emoji_result[0] if emoji_result else '🆕'
        text = f"✅ {amount} ₽ | {emoji} {source} | {wallet}"
        keyboard = get_confirm_keyboard('inc')
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'confirm_inc')
    async def add_income_confirm(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        add_transaction('income', data['amount'], data['source'], data['wallet'])
        await callback.message.edit_text("✅ Доход сохранен!")
        await asyncio.sleep(3)
        await callback.message.delete()
        await state.clear()
        await callback.message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())

    @dp.callback_query(lambda c: c.data == 'change_inc')
    async def add_income_change(callback: types.CallbackQuery, state: FSMContext):
        await state.set_state(AddIncome.amount)
        await callback.message.edit_text("Введите сумму дохода:")
        await callback.answer()

    @dp.callback_query(lambda c: c.data == 'back_inc')
    async def add_income_back(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.delete()
        await callback.message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())
        await callback.answer()

    @dp.message(lambda message: message.text == '📊 Итоги')
    async def summaries(message: types.Message):
        await message.answer("Выберите период или опцию:", reply_markup=get_summaries_keyboard())

    @dp.message(lambda message: message.text in ['📅 Сегодня', '📆 Неделя', '📈 Месяц'])
    async def show_summary(message: types.Message):
        period_map = {'📅 Сегодня': 'day', '📆 Неделя': 'week', '📈 Месяц': 'month'}
        period = period_map[message.text]
        expenses, incomes = get_summary(period)
        total_income = sum(amt for _, amt in incomes) if incomes else 0
        total_expense = sum(amt for _, amt in expenses) if expenses else 0
        balance = total_income - total_expense
        text = f"📊 Итог за {period}:\n────────────────\n💸 Расходы:\n"
        if not expenses:
            text += "- Нет расходов\n"
        for cat, amt in expenses:
            cursor.execute("SELECT emoji FROM categories WHERE name=?", (cat,))
            emoji_result = cursor.fetchone()
            emoji = emoji_result[0] if emoji_result else '🆕'
            text += f"- {emoji} {cat}: {amt} ₽\n"
        text += "\n💰 Доходы:\n"
        if not incomes:
            text += "- Нет доходов\n"
        for cat, amt in incomes:
            cursor.execute("SELECT emoji FROM categories WHERE name=?", (cat,))
            emoji_result = cursor.fetchone()
            emoji = emoji_result[0] if emoji_result else '🆕'
            text += f"- {emoji} {cat}: {amt} ₽\n"
        text += f"\n📈 Баланс: {balance:+} ₽"
        await message.answer(text, reply_markup=get_main_menu())

    @dp.message(lambda message: message.text == '🔎 Итог по категории')
    async def category_summary(message: types.Message):
        keyboard = get_categories_keyboard('both')
        await message.answer("Выберите категорию:", reply_markup=keyboard)

    @dp.callback_query(lambda c: c.data.startswith('cat_both_'), StateFilter(None))
    async def show_category_summary(callback: types.CallbackQuery):
        category = callback.data.split('_')[2]
        data = get_category_summary(category)
        if not data:
            await callback.message.edit_text("Нет данных для этой категории.")
            await callback.answer()
            return
        text = f"Итог по категории {category}:\n"
        for type_, amt in data:
            text += f"{type_.capitalize()}: {amt} ₽\n"
        await callback.message.edit_text(text)
        await callback.answer()

    @dp.message(lambda message: message.text == '💳 Итог по кошельку')
    async def wallet_summary(message: types.Message):
        keyboard = get_wallets_keyboard()
        await message.answer("Выберите кошелек:", reply_markup=keyboard)

    @dp.callback_query(lambda c: c.data.startswith('wallet_'), StateFilter(None))
    async def show_wallet_summary(callback: types.CallbackQuery):
        wallet = callback.data.split('_')[1]
        data = get_wallet_summary(wallet)
        if not data:
            await callback.message.edit_text("Нет данных для этого кошелька.")
            await callback.answer()
            return
        text = f"Итог по кошельку {wallet}:\n"
        for type_, amt in data:
            text += f"{type_.capitalize()}: {amt} ₽\n"
        await callback.message.edit_text(text)
        await callback.answer()

    @dp.message(lambda message: message.text == '📤 Экспорт в CSV')
    async def export_csv(message: types.Message):
        cursor.execute("SELECT * FROM transactions")
        data = cursor.fetchall()
        if not data:
            await message.answer("Нет данных для экспорта.")
            return
        df = pd.DataFrame(data, columns=['id', 'type', 'amount', 'category', 'wallet', 'note', 'date'])
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        await bot.send_document(message.chat.id, types.InputFile(io.BytesIO(csv_buffer.getvalue().encode()), filename='transactions.csv'))
        await message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())

    @dp.message(lambda message: message.text == '📊 Круговая диаграмма')
    async def pie_chart(message: types.Message):
        cursor.execute("SELECT category, SUM(amount) FROM transactions WHERE type='expense' GROUP BY category")
        data = cursor.fetchall()
        if not data:
            await message.answer("Нет данных для диаграммы.", reply_markup=get_main_menu())
            return
        labels = [row[0] for row in data]
        sizes = [row[1] for row in data]
        fig, ax = plt.subplots()
        ax.pie(sizes, labels=labels, autopct='%1.1f%%')
        ax.axis('equal')
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        await bot.send_photo(message.chat.id, photo=buf)
        buf.close()
        plt.close()
        await message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())

    @dp.message(lambda message: message.text == '⚙ Настройки')
    async def settings(message: types.Message, state: FSMContext):
        pin = get_pin()
        if pin:
            await state.set_state(PinCheck.pin)
            await message.answer("Введите PIN для доступа к настройкам:")
        else:
            await message.answer("Выберите опцию настроек:", reply_markup=get_settings_keyboard())

    @dp.message(StateFilter(PinCheck.pin))
    async def check_pin(message: types.Message, state: FSMContext):
        input_pin = message.text.strip()
        pin = get_pin()
        if input_pin == pin:
            await state.clear()
            await message.answer("Доступ разрешён. Выберите опцию настроек:", reply_markup=get_settings_keyboard())
        else:
            await message.answer("Неверный PIN. Попробуйте снова:")

    @dp.message(lambda message: message.text == '👜 Управление кошельками')
    async def manage_wallets(message: types.Message):
        keyboard = get_manage_keyboard('wallet')
        await message.answer("Управление кошельками:", reply_markup=keyboard)

    @dp.callback_query(lambda c: c.data == 'add_wallet')
    async def add_wallet_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_text("Введите название нового кошелька:")
        await state.set_state(Settings.wallet_add)
        await callback.answer()

    @dp.message(StateFilter(Settings.wallet_add))
    async def add_wallet_finish(message: types.Message, state: FSMContext):
        name = message.text.strip()
        if add_wallet(name):
            await message.answer("Кошелек добавлен!", reply_markup=get_settings_keyboard())
        else:
            await message.answer("Кошелек уже существует.")
        await state.clear()

    @dp.callback_query(lambda c: c.data == 'delete_wallet')
    async def delete_wallet_start(callback: types.CallbackQuery, state: FSMContext):
        keyboard = get_wallets_keyboard()
        await callback.message.edit_text("Выберите кошелек для удаления:", reply_markup=keyboard)
        await state.set_state(Settings.wallet_delete)
        await callback.answer()

    @dp.callback_query(StateFilter(Settings.wallet_delete), lambda c: c.data.startswith('wallet_'))
    async def delete_wallet_finish(callback: types.CallbackQuery, state: FSMContext):
        name = callback.data.split('_')[1]
        delete_wallet(name)
        await callback.message.edit_text("Кошелек удален!")
        await state.clear()
        await callback.message.answer("Выберите опцию настроек:", reply_markup=get_settings_keyboard())

    @dp.message(lambda message: message.text == '📂 Управление категориями')
    async def manage_categories(message: types.Message):
        keyboard = get_manage_keyboard('category')
        await message.answer("Управление категориями:", reply_markup=keyboard)

    @dp.callback_query(lambda c: c.data == 'add_category')
    async def add_category_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_text("Введите название новой категории:")
        await state.set_state(Settings.category_add)
        await callback.answer()

    @dp.message(StateFilter(Settings.category_add))
    async def add_category_finish(message: types.Message, state: FSMContext):
        name = message.text.strip()
        kind = 'both'  # По умолчанию
        if add_category(name, '🆕', kind):
            await message.answer("Категория добавлена!", reply_markup=get_settings_keyboard())
        else:
            await message.answer("Категория уже существует.")
        await state.clear()

    @dp.callback_query(lambda c: c.data == 'delete_category')
    async def delete_category_start(callback: types.CallbackQuery, state: FSMContext):
        keyboard = get_categories_keyboard('both')
        await callback.message.edit_text("Выберите категорию для удаления:", reply_markup=keyboard)
        await state.set_state(Settings.category_delete)
        await callback.answer()

    @dp.callback_query(StateFilter(Settings.category_delete), lambda c: c.data.startswith('cat_both_'))
    async def delete_category_finish(callback: types.CallbackQuery, state: FSMContext):
        name = callback.data.split('_')[2]
        delete_category(name)
        await callback.message.edit_text("Категория удалена!")
        await state.clear()
        await callback.message.answer("Выберите опцию настроек:", reply_markup=get_settings_keyboard())

    @dp.message(lambda message: message.text == '🎯 Цели и лимиты')
    async def manage_goals(message: types.Message):
        goals = get_goals()
        text = "Текущие цели:\n"
        if not goals:
            text += "- Нет целей\n"
        for goal in goals:
            text += f"{goal[1]}: {goal[3]}/{goal[2]} ₽ (текущий: {goal[3]})\n"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить цель", callback_data="add_goal")]
        ])
        await message.answer(text, reply_markup=keyboard)

    @dp.callback_query(lambda c: c.data == 'add_goal')
    async def add_goal_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_text("Введите описание цели и целевую сумму (например: Отпуск 100000):")
        await state.set_state(Settings.goal_set)
        await callback.answer()

    @dp.message(StateFilter(Settings.goal_set))
    async def add_goal_finish(message: types.Message, state: FSMContext):
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Неверный формат. Пример: Отпуск 100000")
            return
        description = ' '.join(parts[:-1])
        try:
            target = float(parts[-1])
            add_goal(description, target)
            await message.answer("Цель добавлена!", reply_markup=get_settings_keyboard())
            await state.clear()
        except ValueError:
            await message.answer("Целевая сумма должна быть числом.")

    @dp.message(lambda message: message.text == '⏰ Напоминания')
    async def set_reminder(message: types.Message, state: FSMContext):
        await message.answer("Введите время напоминания (HH:MM):")
        await state.set_state(Settings.reminder_set)

    @dp.message(StateFilter(Settings.reminder_set))
    async def set_reminder_finish(message: types.Message, state: FSMContext):
        time_ = message.text.strip()
        try:
            hour, minute = map(int, time_.split(':'))
            if 0 <= hour < 24 and 0 <= minute < 60:
                set_reminder_time(time_)
                scheduler.remove_all_jobs()
                setup_reminders()
                await message.answer("Время напоминания установлено!", reply_markup=get_settings_keyboard())
                await state.clear()
            else:
                await message.answer("Неверный формат времени. Попробуйте HH:MM (например, 22:00).")
        except ValueError:
            await message.answer("Неверный формат. Пример: 22:00")

    @dp.message(lambda message: message.text == '🔑 PIN-код')
    async def set_pin_handler(message: types.Message, state: FSMContext):
        await message.answer("Введите новый PIN-код (4 цифры, или пусто для отключения):")
        await state.set_state(Settings.pin_set)

    @dp.message(StateFilter(Settings.pin_set))
    async def set_pin_finish(message: types.Message, state: FSMContext):
        pin = message.text.strip() or None
        if pin and (not pin.isdigit() or len(pin) != 4):
            await message.answer("PIN должен быть 4 цифрами. Попробуйте снова.")
            return
        set_pin(pin)
        text = "PIN-код отключен." if not pin else "PIN-код установлен."
        await message.answer(text, reply_markup=get_settings_keyboard())
        await state.clear()

    @dp.message(lambda message: message.text == '💾 Экспорт / бэкап БД')
    async def backup_db(message: types.Message):
        with open('finance_bot.db', 'rb') as db_file:
            await bot.send_document(message.chat.id, types.InputFile(db_file, filename='finance_bot_backup.db'))
        await message.answer("Бэкап БД отправлен!", reply_markup=get_settings_keyboard())

    @dp.message(lambda message: message.text == 'Назад')
    async def back_to_main(message: types.Message, state: FSMContext):
        await state.clear()
        await message.answer("💼 Ты в своём кошельке", reply_markup=get_main_menu())

    @dp.message(Command('e'))
    async def quick_expense(message: types.Message):
        parts = message.text.split()[1:]
        if len(parts) >= 3:
            try:
                amount = float(parts[0])
                category = parts[1]
                wallet = ' '.join(parts[2:])
                cursor.execute("SELECT 1 FROM categories WHERE name=? AND kind IN ('expense', 'both')", (category,))
                if not cursor.fetchone():
                    await message.answer("Категория не найдена.", reply_markup=get_main_menu())
                    return
                cursor.execute("SELECT 1 FROM wallets WHERE name=?", (wallet,))
                if not cursor.fetchone():
                    await message.answer("Кошелек не найден.", reply_markup=get_main_menu())
                    return
                add_transaction('expense', amount, category, wallet)
                await message.answer("✅ Расход сохранен быстро!", reply_markup=get_main_menu())
            except ValueError:
                await message.answer("Неверный формат. Пример: /e 500 еда наличные", reply_markup=get_main_menu())
        else:
            await message.answer("Неверный формат. Пример: /e 500 еда наличные", reply_markup=get_main_menu())

    @dp.message(Command('i'))
    async def quick_income(message: types.Message):
        parts = message.text.split()[1:]
        if len(parts) >= 3:
            try:
                amount = float(parts[0])
                source = parts[1]
                wallet = ' '.join(parts[2:])
                cursor.execute("SELECT 1 FROM categories WHERE name=? AND kind IN ('income', 'both')", (source,))
                if not cursor.fetchone():
                    await message.answer("Источник не найден.", reply_markup=get_main_menu())
                    return
                cursor.execute("SELECT 1 FROM wallets WHERE name=?", (wallet,))
                if not cursor.fetchone():
                    await message.answer("Кошелек не найден.", reply_markup=get_main_menu())
                    return
                add_transaction('income', amount, source, wallet)
                await message.answer("✅ Доход сохранен быстро!", reply_markup=get_main_menu())
            except ValueError:
                await message.answer("Неверный формат. Пример: /i 2000 зарплата карта", reply_markup=get_main_menu())
        else:
            await message.answer("Неверный формат. Пример: /i 2000 зарплата карта", reply_markup=get_main_menu())