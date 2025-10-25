import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from aiogram import Bot

from .storage import ensure_user_dirs

LOGGER = logging.getLogger(__name__)


def _append_json_line(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


async def record_support_request(
    user_id: int,
    *,
    name: str,
    allow_tag: bool,
    issue: str,
    telegram_username: Optional[str],
) -> Path:
    entry = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "name": name,
        "allow_tag": allow_tag,
        "telegram_username": telegram_username,
        "issue": issue,
    }

    dirs = ensure_user_dirs(user_id)
    support_file = dirs["root"] / "support_requests.jsonl"
    await asyncio.to_thread(_append_json_line, support_file, entry)
    LOGGER.info("Support request stored for user %s at %s", user_id, support_file)
    return support_file


async def notify_support_channel(
    bot: Bot,
    channel_id: int,
    *,
    user_id: int,
    name: str,
    allow_tag: bool,
    issue: str,
    telegram_username: Optional[str],
) -> None:
    username_display = f"@{telegram_username}" if telegram_username else "не указан"
    tag_status = "разрешено" if allow_tag else "запрещено"
    profile_link = f"https://t.me/{telegram_username}" if telegram_username else f"tg://openmessage?user_id={user_id}"

    text = (
        "🆘 <b>Новая заявка в поддержку</b>\n"
        f"ID пользователя: <code>{user_id}</code>\n"
        f"Имя: {name}\n"
        f"Telegram: {username_display}\n"
        f"Использование тега: {tag_status}\n"
        f"Ссылка: {profile_link}\n"
        f"Описание: {issue}"
    )

    await bot.send_message(channel_id, text, parse_mode="HTML", disable_web_page_preview=True)
