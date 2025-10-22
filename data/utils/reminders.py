import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from aiogram import Bot

from ..models.user import User
from ..utils.db_utils import get_summary


async def reminder_loop(bot: Bot, poll_interval: int = 60):
    """
    Периодически проверяет пользователей с включенными напоминаниями и отправляет сообщения.
    """
    while True:
        await _process_reminders(bot)
        await asyncio.sleep(poll_interval)


async def _process_reminders(bot: Bot):
    users = await User.filter(daily_reminder_enabled=True).all()
    for user in users:
        tz = _safe_timezone(user.timezone)
        now_local = datetime.now(tz)

        try:
            reminder_hour, reminder_minute = _parse_time(user.reminder_time)
        except ValueError:
            continue

        if now_local.hour != reminder_hour or now_local.minute != reminder_minute:
            continue

        if user.last_reminder_sent and user.last_reminder_sent.date() == now_local.date():
            continue

        start_of_day = datetime.combine(now_local.date(), datetime.min.time())
        summary = await get_summary(
            user,
            start=start_of_day,
            end=now_local.replace(tzinfo=None)
        )
        await bot.send_message(
            user.id,
            "⏰ Напоминание: не забудь записать сегодняшние расходы!\n"
            f"💸 Уже потрачено сегодня: {summary['expense']:.2f} {user.currency}"
        )
        user.last_reminder_sent = now_local.replace(tzinfo=None)
        await user.save()


def _parse_time(time_str: str) -> tuple[int, int]:
    hour_str, minute_str = time_str.split(':', maxsplit=1)
    return int(hour_str), int(minute_str)


def _safe_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")
