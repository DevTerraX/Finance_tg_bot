from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from ..utils.db_utils import get_or_create_user
from ..utils.cleanup import clean_chat
from ..keyboards.main_menu import get_main_menu
from config import AGREEMENT_FILE


async def start_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)

    if not user.name:
        user.name = message.from_user.full_name or f"User {user.id}"
        await user.save()

    if user.agreement_accepted:
        await state.finish()
        reply = await message.answer(f"💫 С возвращением, {user.name}! Финансовый космос уже скучал.", reply_markup=get_main_menu())
        if user.clean_chat:
            await clean_chat(message.bot, message.chat.id, reply.message_id)
        return

    await message.answer(
        "👋 Привет! Я FinTrack — твой проводник по личным финансам.\n"
        "Перед полётом давай заглянем в соглашение, чтобы всё было честно."
    )

    with open(AGREEMENT_FILE, 'rb') as file:
        await message.answer_document(file, caption="📄 Пролистай документ и нажми кнопку ниже, если всё устраивает.")

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Принимаю", callback_data="agree"),
        types.InlineKeyboardButton("❌ Отказываюсь", callback_data="disagree")
    )
    await message.answer("Готов лететь вместе?", reply_markup=keyboard)


async def agree_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    user.agreement_accepted = True
    await user.save()

    await query.message.edit_text("Спасибо за доверие! Погнали управлять бюджетом.")
    menu_message = await query.bot.send_message(
        query.from_user.id,
        f"🚀 Добро пожаловать в центр управления, {user.name}:",
        reply_markup=get_main_menu()
    )
    if user.clean_chat:
        await clean_chat(query.bot, query.message.chat.id, menu_message.message_id)


async def disagree_callback(query: types.CallbackQuery, state: FSMContext):
    await query.message.edit_text("😔 Жаль. Вернись, когда будешь готов продолжить.")


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=['start'], state='*')
    dp.register_callback_query_handler(agree_callback, lambda q: q.data == 'agree')
    dp.register_callback_query_handler(disagree_callback, lambda q: q.data == 'disagree')
