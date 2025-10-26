import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from aiogram import types

from .cleanup import schedule_cleanup


class SessionCleanupManager:
    def __init__(self) -> None:
        self._session_messages: Dict[Tuple[int, str], List[types.Message]] = defaultdict(list)

    def start(self, user_id: int, session_key: str) -> None:
        self._session_messages.pop((user_id, session_key), None)

    def track(self, user_id: int, session_key: str, message: Optional[types.Message]) -> None:
        if not message:
            return
        self._session_messages[(user_id, session_key)].append(message)

    async def finish(
        self,
        user,
        session_key: str,
        *,
        mode: str = "standard",
        keep_last: Optional[types.Message] = None,
    ) -> None:
        key = (user.id, session_key)
        messages = self._session_messages.pop(key, [])
        if keep_last and keep_last in messages:
            messages.remove(keep_last)

        # fallback delays: 3s for aggressive, 10s for standard
        delay = 3 if getattr(user, "cleanup_mode", "standard") == "aggressive" else 10

        for msg in messages:
            await schedule_cleanup(user, msg, category="prompt", delay=delay, delete_history=False)


session_cleanup = SessionCleanupManager()


def track_session_message(user_id: int, session_key: str, message: Optional[types.Message]) -> Optional[types.Message]:
    session_cleanup.track(user_id, session_key, message)
    return message
