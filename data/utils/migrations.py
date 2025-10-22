from __future__ import annotations

from typing import Optional, Set

from tortoise import Tortoise


async def ensure_schema() -> None:
    connection = Tortoise.get_connection("default")
    await _ensure_user_columns(connection)
    await _ensure_transaction_columns(connection)


async def _ensure_user_columns(connection) -> None:
    columns = await _get_columns(connection, "users")

    async def add_column(column: str, ddl: str, post_update: Optional[str] = None) -> None:
        if column in columns:
            return
        await connection.execute_query(ddl)
        if post_update:
            await connection.execute_query(post_update)

    await add_column("name", "ALTER TABLE users ADD COLUMN name VARCHAR(255) NOT NULL DEFAULT ''")
    await add_column("currency", "ALTER TABLE users ADD COLUMN currency VARCHAR(8) NOT NULL DEFAULT '₽'")
    await add_column("timezone", "ALTER TABLE users ADD COLUMN timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Moscow'")
    await add_column("date_format", "ALTER TABLE users ADD COLUMN date_format VARCHAR(32) NOT NULL DEFAULT 'DD.MM.YYYY'")
    await add_column("daily_reminder_enabled", "ALTER TABLE users ADD COLUMN daily_reminder_enabled INT NOT NULL DEFAULT 0")
    await add_column("reminder_time", "ALTER TABLE users ADD COLUMN reminder_time VARCHAR(5) NOT NULL DEFAULT '20:00'")
    await add_column(
        "created_at",
        "ALTER TABLE users ADD COLUMN created_at TIMESTAMP",
        "UPDATE users SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)"
    )
    await add_column("last_reminder_sent", "ALTER TABLE users ADD COLUMN last_reminder_sent TIMESTAMP")


async def _ensure_transaction_columns(connection) -> None:
    columns = await _get_columns(connection, "transactions")
    if "check_photo_path" not in columns:
        await connection.execute_query("ALTER TABLE transactions ADD COLUMN check_photo_path VARCHAR(255)")


async def _get_columns(connection, table: str) -> Set[str]:
    rows = await connection.execute_query_dict(f"PRAGMA table_info({table})")
    return {row["name"] for row in rows}
