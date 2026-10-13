from fastapi import Cookie, HTTPException

from services.redis_service import get_session_user_id


async def get_optional_current_user_id(
    session_id: str | None = Cookie(default=None),
) -> int | None:
    return await get_session_user_id(session_id)


async def get_current_user_id(
    session_id: str | None = Cookie(default=None),
) -> int:
    user_id = await get_session_user_id(session_id)

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Требуется аутентификация",
        )

    return user_id
