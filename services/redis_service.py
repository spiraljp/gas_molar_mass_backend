import json
from uuid import uuid4

import redis.asyncio as redis

REDIS_URL = "redis://localhost:6379/0"
SESSION_TTL_SECONDS = 60 * 60 * 24

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
)


async def create_session(user_id: int, username: str) -> str:
    session_id = str(uuid4())
    key = f"session:{session_id}"

    await redis_client.set(
        key,
        json.dumps({
            "user_id": user_id,
            "username": username,
        }),
        ex=SESSION_TTL_SECONDS,
    )

    return session_id


async def get_session_user_id(session_id: str | None) -> int | None:
    if not session_id:
        return None

    key = f"session:{session_id}"
    raw_session = await redis_client.get(key)

    if raw_session is None:
        return None

    session_data = json.loads(raw_session)
    return int(session_data["user_id"])


async def delete_session(session_id: str | None) -> None:
    if not session_id:
        return

    key = f"session:{session_id}"
    await redis_client.delete(key)
