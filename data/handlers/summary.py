# data/handlers/summary.py
from aiogram import types
from aiogram.dispatcher import FSMContext, Dispatcher
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from ..utils.db_utils import get_summary, get_or_create_user 
from ..utils.charts import generate_pie_chart
from ..utils.csv_export import export_to_csv
from ..keyboards.main_menu import get_main_menu, get_back_keyboard

def get_summary_keyboard():  # Измените на reply
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("Простая сводка"),
        KeyboardButton("Диаграмма"),
        KeyboardButton("CSV-файл"),
        KeyboardButton("Выбрать период"),
        KeyboardButton("Назад")
    )
    return keyboard

async def show_summary_menu(message: types.Message):
    await message.answer("Итоги:", reply_markup=get_summary_keyboard())

async def summary_handler(message: types.Message, state: FSMContext):  # Новый handler для текстовых кнопок
    data = message.text
    user = await get_or_create_user(message.from_user.id)
    summary_data = await get_summary(user)  # По умолчанию 'all'
    if data == "Простая сводка":
        text = f"Баланс: {summary_data['balance']}\nДоходы: {summary_data['income']}\nРасходы: {summary_data['expense']}"
        await message.answer(text, reply_markup=get_summary_keyboard())
    elif data == "Диаграмма":
        exp_data = {}
        for tx in summary_data['expenses']:
            cat = tx.category_name or 'Другое'
            exp_data[cat] = exp_data.get(cat, 0) + tx.amount
        path = generate_pie_chart(exp_data, 'Расходы')
        if path:
            with open(path, 'rb') as photo:
                await message.answer_photo(photo)
        await message.answer("Диаграмма отправлена.", reply_markup=get_summary_keyboard())
    elif data == "CSV-файл":
        all_tx = summary_data['incomes'] + summary_data['expenses']
        path = export_to_csv(all_tx, 'finance_summary')
        with open(path, 'rb') as file:
            await message.answer_document(file)
    elif data == "Выбрать период":
        await message.answer("Введите период (день/неделя/месяц):", reply_markup=get_back_keyboard())
        # Добавьте состояние для ввода периода
    elif data == "Назад":
        await message.answer("Возвращаемся в меню.", reply_markup=get_main_menu())

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(summary_handler, lambda m: m.text in ['Простая сводка', 'Диаграмма', 'CSV-файл', 'Выбрать период', 'Назад'])