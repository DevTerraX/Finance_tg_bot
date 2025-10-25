import asyncio
from typing import Optional, Dict

from aiogram import Bot, types

CLEANUP_DELAYS: Dict[str, Dict[str, int]] = {
    "standard": {
        "prompt": 10,
        "result": 45,
        "attachment": 300,
        "user": 7,
    },
    "aggressive": {
        "prompt": 5,
        "result": 20,
        "attachment": 150,
        "user": 5,
    },
}

CATEGORY_ALIAS = {
    "text": "prompt",
    "prompt": "prompt",
    "long": "result",
    "result": "result",
    "attachment": "attachment",
    "user": "user",
}

DEFAULT_DELAY = 60


async def schedule_cleanup(
    user,
    message: Optional[types.Message],
    category: str = "text",
    delay: Optional[int] = None,
    limit: int = 200,
    delete_history: bool = False,
) -> None:
    if not message or not user.clean_chat:
        return

    mode = getattr(user, "cleanup_mode", "standard")
    if mode not in CLEANUP_DELAYS:
        mode = "standard"

    category_key = CATEGORY_ALIAS.get(category, category)
    cleanup_delay = delay if delay is not None else CLEANUP_DELAYS[mode].get(category_key, DEFAULT_DELAY)
    if cleanup_delay <= 0:
        return

    effective_delete_history = delete_history or (mode == "aggressive" and category_key in {"prompt", "user", "result"})

    asyncio.create_task(
        _cleanup_after_delay(
            message.bot,
            message.chat.id,
            message.message_id,
            cleanup_delay,
            limit,
            effective_delete_history,
        )
    )


async def _cleanup_after_delay(bot: Bot, chat_id: int, message_id: int, delay: int, limit: int, delete_history: bool) -> None:
    await asyncio.sleep(delay)
    if delete_history:
        for current_id in range(message_id, max(message_id - limit, 0), -1):
            try:
                await bot.delete_message(chat_id, current_id)
            except Exception:
                continue
    else:
        try:
            await bot.delete_message(chat_id, message_id)
        except Exception:
            pass


async def schedule_user_message_cleanup(user, message: Optional[types.Message], delay: int = 6) -> None:
    await schedule_cleanup(user, message, category="user", delay=delay, delete_history=False)


async def schedule_prompt_cleanup(user, message: Optional[types.Message]) -> None:
    await schedule_cleanup(user, message, category="prompt", delete_history=True)


async def schedule_result_cleanup(user, message: Optional[types.Message]) -> None:
    await schedule_cleanup(user, message, category="result", delete_history=True)
