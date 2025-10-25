from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext

from config import SUPPORT_CHANNEL_ID
from ..utils.db_utils import (
    get_or_create_user,
    get_categories,
    create_category,
    delete_category
)
from ..utils.cleanup import (
    schedule_user_message_cleanup,
    schedule_prompt_cleanup,
    schedule_result_cleanup,
)
from ..utils.support import record_support_request, notify_support_channel
from ..keyboards.main_menu import get_main_menu, BACK_BUTTON, SETTINGS_BUTTON
from ..keyboards.category import get_categories_keyboard
from ..keyboards.settings import (
    get_settings_keyboard,
    get_profile_keyboard,
    get_notifications_keyboard,
    get_category_management_keyboard,
    get_cancel_keyboard,
    PROFILE_BUTTON,
    EXPENSE_CATEGORIES_BUTTON,
    INCOME_CATEGORIES_BUTTON,
    NOTIFICATIONS_BUTTON,
    SUPPORT_BUTTON,
    AUTO_CLEAN_PREFIX,
    CLEAN_MODE_PREFIX,
    CATEGORY_ADD_BUTTON,
    CATEGORY_DELETE_BUTTON,
    CANCEL_BUTTON
)
from ..keyboards.support import (
    get_support_name_keyboard,
    get_support_tag_keyboard,
    get_support_issue_keyboard,
    get_support_confirmation_keyboard,
    SUPPORT_ALLOW_TAG_YES,
    SUPPORT_ALLOW_TAG_NO,
    SUPPORT_CONFIRM_BUTTON,
)
from ..states.settings_states import SettingsStates

logger = logging.getLogger(__name__)


async def open_settings(message: types.Message, state: FSMContext):
    await state.finish()
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await SettingsStates.root.set()
    reply = await message.answer("⚙️ Настройки: выбери, что настроить.", reply_markup=get_settings_keyboard())
    await schedule_result_cleanup(user, reply)


async def settings_root_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text

    if text == PROFILE_BUTTON:
        await SettingsStates.profile_menu.set()
        reply = await message.answer("👤 Управление профилем:", reply_markup=get_profile_keyboard(user))
        await schedule_result_cleanup(user, reply)
    elif text == EXPENSE_CATEGORIES_BUTTON:
        await SettingsStates.categories_menu.set()
        await state.update_data(category_type='expense')
        reply = await message.answer("📂 Категории расходов:", reply_markup=get_category_management_keyboard())
        await schedule_result_cleanup(user, reply)
    elif text == INCOME_CATEGORIES_BUTTON:
        await SettingsStates.categories_menu.set()
        await state.update_data(category_type='income')
        reply = await message.answer("💰 Категории доходов:", reply_markup=get_category_management_keyboard())
        await schedule_result_cleanup(user, reply)
    elif text == NOTIFICATIONS_BUTTON:
        await SettingsStates.notifications_menu.set()
        reply = await message.answer("🔔 Управление напоминаниями:", reply_markup=get_notifications_keyboard(user))
        await schedule_result_cleanup(user, reply)
    elif text == SUPPORT_BUTTON:
        await SettingsStates.support_collect_name.set()
        await state.update_data({
            "support_name": None,
            "support_allow_tag": None,
            "support_issue": None,
        })
        reply = await message.answer(
            "🆘 Служба поддержки. Как нам к вам обращаться?",
            reply_markup=get_support_name_keyboard()
        )
        await schedule_prompt_cleanup(user, reply)
    elif text == BACK_BUTTON:
        await state.finish()
        await message.answer("🏠 Возвращаю в главное меню.", reply_markup=get_main_menu())
    else:
        reply = await message.answer("Пожалуйста, выбери пункт из списка ниже.", reply_markup=get_settings_keyboard())
        await schedule_prompt_cleanup(user, reply)


async def _send_support_summary(message: types.Message, user, state: FSMContext):
    data = await state.get_data()
    name = (data.get("support_name") or "").strip() or "Не указано"
    allow_tag = bool(data.get("support_allow_tag"))
    issue = (data.get("support_issue") or "").strip() or "Не описано"
    username = message.from_user.username

    if allow_tag and username:
        tag_text = f"Можно использовать (@{username})"
        contact_hint = "✅ Мы сможем написать тебе напрямую."
    elif allow_tag:
        tag_text = "Можно использовать"
        contact_hint = "ℹ️ У тебя пока нет Telegram-тега, поэтому ответ появится в этом чате."
    else:
        tag_text = "Не использовать"
        contact_hint = "⚠️ Без разрешения на тег мы не сможем написать первыми — заглядывай в этот чат."

    summary = (
        "🆘 Проверь данные заявки перед отправкой:\n"
        f"Имя: {name}\n"
        f"Telegram тег: {tag_text}\n"
        f"Проблема: {issue}\n"
        f"{contact_hint}\n\n"
        "Если всё верно, нажми «✅ Подтверждение» или измени данные."
    )
    reply = await message.answer(summary, reply_markup=get_support_confirmation_keyboard(user.clean_chat))
    await schedule_result_cleanup(user, reply)


async def support_name_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = (message.text or "").strip()

    if message.text == BACK_BUTTON:
        await state.reset_data()
        await SettingsStates.root.set()
        reply = await message.answer("⚙️ Выбери следующий раздел настроек:", reply_markup=get_settings_keyboard())
        await schedule_result_cleanup(user, reply)
        return

    if not text:
        reply = await message.answer("⚠️ Имя не может быть пустым. Попробуй снова.", reply_markup=get_support_name_keyboard())
        await schedule_prompt_cleanup(user, reply)
        return

    await state.update_data(support_name=text[:100])
    await SettingsStates.support_collect_tag_permission.set()
    reply = await message.answer(
        "📨 Можно ли использовать твой Telegram тег для связи?",
        reply_markup=get_support_tag_keyboard()
    )
    await schedule_prompt_cleanup(user, reply)


async def support_tag_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text

    if text == BACK_BUTTON:
        await SettingsStates.support_collect_name.set()
        current_name = (await state.get_data()).get("support_name") or ""
        prompt = "📝 Укажи имя для связи с поддержкой:"
        if current_name:
            prompt += f"\nТекущее значение: {current_name}"
        reply = await message.answer(prompt, reply_markup=get_support_name_keyboard())
        await schedule_prompt_cleanup(user, reply)
        return

    if text == SUPPORT_ALLOW_TAG_YES:
        allow_tag = True
    elif text == SUPPORT_ALLOW_TAG_NO:
        allow_tag = False
    else:
        reply = await message.answer("Пожалуйста, выбери один из вариантов на клавиатуре.", reply_markup=get_support_tag_keyboard())
        await schedule_prompt_cleanup(user, reply)
        return

    await state.update_data(support_allow_tag=allow_tag)
    await SettingsStates.support_collect_issue.set()
    reply = await message.answer(
        "📝 Расскажи, что работает плохо или не работает вовсе.",
        reply_markup=get_support_issue_keyboard()
    )
    await schedule_prompt_cleanup(user, reply)


async def support_issue_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text

    if text == BACK_BUTTON:
        await SettingsStates.support_collect_tag_permission.set()
        reply = await message.answer(
            "📨 Можно ли использовать твой Telegram тег для связи?",
            reply_markup=get_support_tag_keyboard()
        )
        await schedule_prompt_cleanup(user, reply)
        return

    issue = (text or "").strip()
    if not issue:
        reply = await message.answer("⚠️ Опиши, пожалуйста, проблему, чтобы мы могли помочь.", reply_markup=get_support_issue_keyboard())
        await schedule_prompt_cleanup(user, reply)
        return

    await state.update_data(support_issue=issue[:1000])
    await SettingsStates.support_confirmation.set()
    await _send_support_summary(message, user, state)


async def support_confirmation_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text or ""

    if text == BACK_BUTTON:
        await SettingsStates.support_collect_issue.set()
        reply = await message.answer(
            "📝 Расскажи, что работает плохо или не работает вовсе.",
            reply_markup=get_support_issue_keyboard()
        )
        await schedule_prompt_cleanup(user, reply)
        return

    if text.startswith(AUTO_CLEAN_PREFIX):
        user.clean_chat = not user.clean_chat
        await user.save()
        status = 'включена' if user.clean_chat else 'выключена'
        notify = await message.answer(f"🧹 Автоочистка теперь {status}.", reply_markup=get_support_confirmation_keyboard(user.clean_chat))
        await schedule_result_cleanup(user, notify)
        await _send_support_summary(message, user, state)
        return

    if text == SUPPORT_CONFIRM_BUTTON:
        data = await state.get_data()
        name = (data.get("support_name") or user.name or message.from_user.full_name or "").strip() or "Не указано"
        allow_tag_value = data.get("support_allow_tag")
        allow_tag = bool(allow_tag_value) if allow_tag_value is not None else False
        issue = (data.get("support_issue") or "").strip() or "Не описано"
        try:
            await record_support_request(
                user.id,
                name=name,
                allow_tag=allow_tag,
                issue=issue,
                telegram_username=message.from_user.username,
            )
            if SUPPORT_CHANNEL_ID:
                try:
                    await notify_support_channel(
                        message.bot,
                        SUPPORT_CHANNEL_ID,
                        user_id=user.id,
                        name=name,
                        allow_tag=allow_tag,
                        issue=issue,
                        telegram_username=message.from_user.username,
                    )
                except Exception as exc:
                    logger.error(
                        "Failed to notify support channel %s for user %s: %s",
                        SUPPORT_CHANNEL_ID,
                        user.id,
                        exc,
                    )
        except Exception as exc:
            logger.error("Failed to record support request for user %s: %s", user.id, exc)
            reply = await message.answer(
                "⚠️ Не удалось сохранить заявку. Попробуй ещё раз позже.",
                reply_markup=get_support_confirmation_keyboard(user.clean_chat)
            )
            await schedule_prompt_cleanup(user, reply)
            return

        await state.reset_data()
        await SettingsStates.root.set()
        username = message.from_user.username
        if allow_tag and username:
            contact_text = "Мы свяжемся с тобой в ближайшее время."
        elif allow_tag and not username:
            contact_text = "Ответ появится прямо в этом чате, потому что у тебя нет Telegram-тега."
        else:
            contact_text = (
                "Ты запретил использовать Telegram-тег, поэтому мы не сможем написать первыми. "
                "Пожалуйста, заглядывай в этот чат, чтобы увидеть ответ."
            )
        reply = await message.answer(
            f"✅ Заявка отправлена в поддержку.\n{contact_text}",
            reply_markup=get_settings_keyboard()
        )
        await schedule_result_cleanup(user, reply)
        return

    reply = await message.answer(
        "Используй кнопки ниже, чтобы подтвердить или изменить данные.",
        reply_markup=get_support_confirmation_keyboard(user.clean_chat)
    )
    await schedule_prompt_cleanup(user, reply)

async def profile_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text
    reply: types.Message | None = None

    if text.startswith(AUTO_CLEAN_PREFIX):
        user.clean_chat = not user.clean_chat
        await user.save()
        status = 'включена' if user.clean_chat else 'выключена'
        reply = await message.answer(f"🧹 Автоочистка теперь {status}.", reply_markup=get_profile_keyboard(user))
    elif text.startswith(CLEAN_MODE_PREFIX):
        current_mode = getattr(user, "cleanup_mode", "standard")
        user.cleanup_mode = "aggressive" if current_mode == "standard" else "standard"
        await user.save()
        label = "Агрессивно" if user.cleanup_mode == "aggressive" else "Стандарт"
        reply = await message.answer(
            f"⚙️ Режим очистки переключён: {label}.",
            reply_markup=get_profile_keyboard(user)
        )
    elif text == "✏️ Изменить имя":
        await SettingsStates.edit_name.set()
        reply = await message.answer("✏️ Введи новое имя профиля:", reply_markup=get_cancel_keyboard())
    elif text.startswith("💱 Валюта"):
        await SettingsStates.edit_currency.set()
        reply = await message.answer("💱 Укажи символ валюты (например, ₽ или USD):", reply_markup=get_cancel_keyboard())
    elif text.startswith("🌍 Часовой пояс"):
        await SettingsStates.edit_timezone.set()
        reply = await message.answer("🌍 Введи часовой пояс (например, Europe/Moscow):", reply_markup=get_cancel_keyboard())
    elif text.startswith("📅 Формат даты"):
        await SettingsStates.edit_date_format.set()
        reply = await message.answer("📅 Введи формат даты (например, DD.MM.YYYY или YYYY-MM-DD):", reply_markup=get_cancel_keyboard())
    elif text == BACK_BUTTON:
        await SettingsStates.root.set()
        reply = await message.answer("⚙️ Выбери следующий раздел настроек:", reply_markup=get_settings_keyboard())
    else:
        reply = await message.answer("Пожалуйста, выбери действие из меню ниже.", reply_markup=get_profile_keyboard(user))

    if reply:
        if text.startswith((AUTO_CLEAN_PREFIX, CLEAN_MODE_PREFIX)):
            await schedule_result_cleanup(user, reply)
        else:
            await schedule_prompt_cleanup(user, reply)


async def profile_edit_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text.strip()
    text_lower = text.lower()
    current_state = await state.get_state()

    if text == CANCEL_BUTTON or text_lower == CANCEL_BUTTON.lower():
        await SettingsStates.profile_menu.set()
        reply = await message.answer("⛔ Изменения отменены.", reply_markup=get_profile_keyboard(user))
        await schedule_prompt_cleanup(user, reply)
        return

    if current_state == SettingsStates.edit_name.state:
        if not text:
            reply = await message.answer("⚠️ Имя не может быть пустым. Попробуй снова.", reply_markup=get_cancel_keyboard())
            await schedule_prompt_cleanup(user, reply)
            return
        user.name = text[:100]
        await user.save()
        await SettingsStates.profile_menu.set()
        reply = await message.answer(f"✅ Имя обновлено: {user.name}", reply_markup=get_profile_keyboard(user))
        await schedule_result_cleanup(user, reply)
    elif current_state == SettingsStates.edit_currency.state:
        if len(text) > 8:
            reply = await message.answer("⚠️ Символ валюты слишком длинный. Попробуй снова.", reply_markup=get_cancel_keyboard())
            await schedule_prompt_cleanup(user, reply)
            return
        user.currency = text
        await user.save()
        await SettingsStates.profile_menu.set()
        reply = await message.answer(f"✅ Валюта обновлена: {user.currency}", reply_markup=get_profile_keyboard(user))
        await schedule_result_cleanup(user, reply)
    elif current_state == SettingsStates.edit_timezone.state:
        try:
            ZoneInfo(text)
        except ZoneInfoNotFoundError:
            reply = await message.answer("⚠️ Часовой пояс не найден. Пример: Europe/Moscow.", reply_markup=get_cancel_keyboard())
            await schedule_prompt_cleanup(user, reply)
            return
        user.timezone = text
        await user.save()
        await SettingsStates.profile_menu.set()
        reply = await message.answer(f"✅ Часовой пояс обновлён: {user.timezone}", reply_markup=get_profile_keyboard(user))
        await schedule_result_cleanup(user, reply)
    elif current_state == SettingsStates.edit_date_format.state:
        if not _is_valid_date_format(text):
            reply = await message.answer("⚠️ Некорректный формат. Используй комбинацию DD, MM, YYYY.", reply_markup=get_cancel_keyboard())
            await schedule_prompt_cleanup(user, reply)
            return
        user.date_format = text
        await user.save()
        await SettingsStates.profile_menu.set()
        reply = await message.answer(f"✅ Формат даты обновлён: {user.date_format}", reply_markup=get_profile_keyboard(user))
        await schedule_result_cleanup(user, reply)


def _is_valid_date_format(pattern: str) -> bool:
    tokens = {"DD", "MM", "YYYY"}
    return all(token in pattern for token in tokens) and len(pattern) <= 16


async def notifications_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text

    if text.startswith("🔔 Напоминания"):
        user.daily_reminder_enabled = not user.daily_reminder_enabled
        if not user.daily_reminder_enabled:
            user.last_reminder_sent = None
        await user.save()
        reply = await message.answer(
            f"🔔 Напоминания {'включены' if user.daily_reminder_enabled else 'выключены'}.",
            reply_markup=get_notifications_keyboard(user)
        )
        await schedule_result_cleanup(user, reply)
    elif text.startswith("⏰ Время напоминания"):
        await SettingsStates.edit_reminder_time.set()
        reply = await message.answer("⏰ Введи время в формате ЧЧ:ММ:", reply_markup=get_cancel_keyboard())
        await schedule_prompt_cleanup(user, reply)
    elif text == BACK_BUTTON:
        await SettingsStates.root.set()
        reply = await message.answer("⚙️ Выбери следующий раздел настроек:", reply_markup=get_settings_keyboard())
        await schedule_result_cleanup(user, reply)
    else:
        reply = await message.answer("Пожалуйста, выбери действие из меню ниже.", reply_markup=get_notifications_keyboard(user))
        await schedule_prompt_cleanup(user, reply)


async def reminder_time_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text.strip()
    text_lower = text.lower()

    if text == CANCEL_BUTTON or text_lower == CANCEL_BUTTON.lower():
        await SettingsStates.notifications_menu.set()
        reply = await message.answer("⛔ Изменения отменены.", reply_markup=get_notifications_keyboard(user))
        await schedule_prompt_cleanup(user, reply)
        return

    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        reply = await message.answer("⚠️ Некорректный формат времени. Используй ЧЧ:ММ.", reply_markup=get_cancel_keyboard())
        await schedule_prompt_cleanup(user, reply)
        return

    user.reminder_time = text
    user.last_reminder_sent = None
    await user.save()
    await SettingsStates.notifications_menu.set()
    reply = await message.answer(f"✅ Время напоминания обновлено: {user.reminder_time}", reply_markup=get_notifications_keyboard(user))
    await schedule_result_cleanup(user, reply)


async def categories_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text
    state_data = await state.get_data()
    category_type = state_data.get('category_type', 'expense')

    if text == CATEGORY_ADD_BUTTON:
        await SettingsStates.add_category.set()
        reply = await message.answer("🆕 Введи название новой категории:", reply_markup=get_cancel_keyboard())
        await schedule_prompt_cleanup(user, reply)
    elif text == CATEGORY_DELETE_BUTTON:
        categories = await get_categories(user, category_type)
        if not categories:
            reply = await message.answer("⚠️ Нет категорий для удаления.", reply_markup=get_category_management_keyboard())
            await schedule_prompt_cleanup(user, reply)
            return
        keyboard = get_categories_keyboard(categories, type=category_type, for_delete=True)
        reply = await message.answer("🗑️ Выбери категорию для удаления:", reply_markup=keyboard)
        await schedule_result_cleanup(user, reply)
        await SettingsStates.delete_category.set()
    elif text == BACK_BUTTON:
        await SettingsStates.root.set()
        reply = await message.answer("⚙️ Выбери следующий раздел настроек:", reply_markup=get_settings_keyboard())
        await schedule_result_cleanup(user, reply)
    else:
        reply = await message.answer("Используй кнопки меню, чтобы управлять категориями.", reply_markup=get_category_management_keyboard())
        await schedule_prompt_cleanup(user, reply)


async def add_category_handler(message: types.Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id, message.from_user.full_name)
    await schedule_user_message_cleanup(user, message)
    text = message.text.strip()
    text_lower = text.lower()
    if text == CANCEL_BUTTON or text_lower == CANCEL_BUTTON.lower():
        await SettingsStates.categories_menu.set()
        reply = await message.answer("⛔ Добавление отменено.", reply_markup=get_category_management_keyboard())
        await schedule_prompt_cleanup(user, reply)
        return

    if not text:
        reply = await message.answer("⚠️ Название не может быть пустым. Попробуй снова.", reply_markup=get_cancel_keyboard())
        await schedule_prompt_cleanup(user, reply)
        return

    state_data = await state.get_data()
    category_type = state_data.get('category_type', 'expense')
    await create_category(user, text, category_type)
    await SettingsStates.categories_menu.set()
    reply = await message.answer(f"✅ Категория '{text}' добавлена.", reply_markup=get_category_management_keyboard())
    await schedule_result_cleanup(user, reply)


async def delete_category_callback(query: types.CallbackQuery, state: FSMContext):
    data = query.data
    user = await get_or_create_user(query.from_user.id, query.from_user.full_name)
    state_data = await state.get_data()
    category_type = state_data.get('category_type', 'expense')

    if data.startswith('delete_category_'):
        cat_id = int(data.split('_')[-1])
        try:
            await delete_category(user, cat_id)
        except ValueError as exc:
            await query.answer(str(exc), show_alert=True)
            return
        await query.answer("Категория удалена.")
        categories = await get_categories(user, category_type)
        if categories:
            keyboard = get_categories_keyboard(categories, type=category_type, for_delete=True)
            await query.message.edit_text("🗑️ Категория удалена. Выбери следующую:", reply_markup=keyboard)
        else:
            await SettingsStates.categories_menu.set()
            await query.message.edit_text("🗃️ Все категории удалены.", reply_markup=None)
            reply = await query.message.answer("📂 Меню категорий:", reply_markup=get_category_management_keyboard())
            await schedule_result_cleanup(user, reply)
    elif data == 'back':
        await SettingsStates.categories_menu.set()
        await query.message.delete()
        reply = await query.message.answer("📂 Меню категорий:", reply_markup=get_category_management_keyboard())
        await schedule_result_cleanup(user, reply)


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(open_settings, lambda m: m.text == SETTINGS_BUTTON, state="*")
    dp.register_message_handler(settings_root_handler, state=SettingsStates.root)
    dp.register_message_handler(profile_handler, state=SettingsStates.profile_menu)
    dp.register_message_handler(profile_edit_handler, state=[
        SettingsStates.edit_name,
        SettingsStates.edit_currency,
        SettingsStates.edit_timezone,
        SettingsStates.edit_date_format
    ])
    dp.register_message_handler(notifications_handler, state=SettingsStates.notifications_menu)
    dp.register_message_handler(reminder_time_handler, state=SettingsStates.edit_reminder_time)
    dp.register_message_handler(support_name_handler, state=SettingsStates.support_collect_name)
    dp.register_message_handler(support_tag_handler, state=SettingsStates.support_collect_tag_permission)
    dp.register_message_handler(support_issue_handler, state=SettingsStates.support_collect_issue)
    dp.register_message_handler(support_confirmation_handler, state=SettingsStates.support_confirmation)
    dp.register_message_handler(categories_handler, state=SettingsStates.categories_menu)
    dp.register_message_handler(add_category_handler, state=SettingsStates.add_category)
    dp.register_callback_query_handler(delete_category_callback, state=SettingsStates.delete_category)
