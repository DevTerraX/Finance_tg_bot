from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from ..utils.db_utils import get_or_create_user
from ..utils.cleanup import schedule_user_message_cleanup
from ..keyboards.main_menu import get_main_menu
from config import AGREEMENT_FILE


async def start_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)

    if not user.name:
        user.name = message.from_user.full_name or f"User {user.id}"
        await user.save()

    if user.agreement_accepted:
        await state.finish()
        reply = await message.answer(f"💫 С возвращением, {user.name}! Финансовый космос уже скучал.", reply_markup=get_main_menu())
        return

    await message.answer(
        "👋 Привет! Я FinTrack — твой проводник по личным финансам.\n"
        "Перед полётом давай заглянем в соглашение, чтобы всё было честно."
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("✅ Принимаю", callback_data="agree"),
        types.InlineKeyboardButton("❌ Отказываюсь", callback_data="disagree")
    )
    with open(AGREEMENT_FILE, 'rb') as file:
        await message.answer_document(
            file,
            caption="📄 Пролистай документ и нажми кнопку ниже, если всё устраивает.",
            reply_markup=keyboard
        )


async def agree_callback(query: types.CallbackQuery, state: FSMContext):
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    user.agreement_accepted = True
    await user.save()

    await _update_message_caption(query, "Спасибо за доверие! Погнали управлять бюджетом.")
    await query.answer()
    menu_message = await query.bot.send_message(
        query.from_user.id,
        f"🚀 Добро пожаловать в центр управления, {user.name}:",
        reply_markup=get_main_menu()
    )


async def disagree_callback(query: types.CallbackQuery, state: FSMContext):
    await _update_message_caption(query, "😔 Жаль. Вернись, когда будешь готов продолжить.")
    await query.answer()


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_handler, commands=['start'], state='*')
    dp.register_callback_query_handler(agree_callback, lambda q: q.data == 'agree')
    dp.register_callback_query_handler(disagree_callback, lambda q: q.data == 'disagree')


async def _update_message_caption(query: types.CallbackQuery, text: str) -> None:
    if query.message.content_type == 'document':
        await query.message.edit_caption(text)
    else:
        await query.message.edit_text(text)
