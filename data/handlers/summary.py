# handlers/summary.py
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from ..utils.db_utils import get_summary, get_or_create_user
from ..utils.charts import generate_pie_chart
from ..utils.csv_export import export_to_csv
from ..keyboards.summary import get_summary_keyboard
from ..keyboards.main_menu import get_main_menu

async def show_summary_menu(message: types.Message):
    await message.answer("Итоги:", reply_markup=get_summary_keyboard())

async def summary_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    user = await get_or_create_user(query.from_user.id)
    summary_data = await get_summary(user)  # По умолчанию 'all', можно добавить периоды
    if data == 'simple_summary':
        text = f"Баланс: {summary_data['balance']}\nДоходы: {summary_data['income']}\nРасходы: {summary_data['expense']}"
        await query.message.edit_text(text, reply_markup=get_summary_keyboard())
    elif data == 'chart':
        # Диаграмма расходов
        exp_data = {}
        for tx in summary_data['expenses']:
            cat = tx.category_name or 'Другое'
            exp_data[cat] = exp_data.get(cat, 0) + tx.amount
        path = generate_pie_chart(exp_data, 'Расходы')
        if path:
            with open(path, 'rb') as photo:
                await query.bot.send_photo(query.message.chat.id, photo)
        # Аналогично для доходов
    elif data == 'csv':
        all_tx = summary_data['incomes'] + summary_data['expenses']
        path = export_to_csv(all_tx, 'finance_summary')
        with open(path, 'rb') as file:
            await query.bot.send_document(query.message.chat.id, file)
    elif data == 'period':
        # Добавить состояние для выбора периода (день/неделя/месяц)
        await query.message.edit_text("Выберите период: день, неделя, месяц")  # Добавить клавиатуру
    elif data == 'back_to_menu':
        await query.message.edit_text("Главное меню", reply_markup=get_main_menu())

def register_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(summary_callback, lambda q: q.data in ['simple_summary', 'advanced_summary', 'chart', 'csv', 'period', 'back_to_menu'])