# handlers/start.py
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from ..utils.db_utils import get_or_create_user
from config import AGREEMENT_FILE
from ..keyboards.main_menu import get_main_menu

async def start_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    if user.agreement_accepted:
        await message.answer("Добро пожаловать обратно!", reply_markup=get_main_menu())
        return
    
    await message.answer("Привет! Это бот для учета финансов. Быстро и удобно.")
    # Отправка файла соглашения
    with open(AGREEMENT_FILE, 'rb') as file:
        await message.answer_document(file, caption="Пожалуйста, ознакомьтесь с соглашением.")
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Согласиться", callback_data="agree"),
        types.InlineKeyboardButton("Отказаться", callback_data="disagree")
    )
    await message.answer("Согласны?", reply_markup=keyboard)

async def agree_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id)
    user.agreement_accepted = True
    await user.save()
    await query.message.edit_text("Спасибо! Теперь доступен весь функционал.", reply_markup=get_main_menu())

async def disagree_callback(query: types.CallbackQuery, state: FSMContext):
    await query.message.edit_text("Жаль. Бот недоступен без согласия.")

def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=['start'])
    dp.register_callback_query_handler(agree_callback, lambda q: q.data == 'agree')
    dp.register_callback_query_handler(disagree_callback, lambda q: q.data == 'disagree')