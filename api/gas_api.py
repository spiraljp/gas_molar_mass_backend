from collections.abc import Sequence
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.gas import Gas
from models.gas_like import GasLike
from models.user import User
from schemas.gas_schemas import (
    GasActionResponse,
    GasDraftResponse,
    GasFeedItem,
    GasLikeRequest,
    GasListItem,
    GasPublishRequest,
)
from schemas.user_schemas import (
    AuthStubRequest,
    AuthStubResponse,
    UserRegisterRequest,
    UserResponse,
)
from services.current_user_service import (
    get_current_user_id,
    get_optional_current_user_id,
)
from services.minio_service import upload_file_to_minio
from services.password_service import hash_password, verify_password
from services.redis_service import create_session, delete_session

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DEFAULT_IMAGE_URL = "/static/img/default-gas.png"
DEFAULT_VIDEO_URL = "/static/img/default-gas-video.mp4"


def get_media_url(value: str | None, default_value: str) -> str:
    if value:
        return value
    return default_value


async def get_like_counts(db: AsyncSession) -> dict[int, int]:
    result = await db.execute(
        select(GasLike.gas_id, func.count(GasLike.id))
        .group_by(GasLike.gas_id)
    )

    return {gas_id: likes_count for gas_id, likes_count in result.all()}


async def attach_view_data(gases: Sequence[Gas], db: AsyncSession) -> list[dict]:
    like_counts = await get_like_counts(db)

    return [
        {
            "id": gas.id,
            "title": gas.gas_name,
            "formula": gas.gas_formula,
            "description": gas.short_description,
            "molar_mass": gas.molar_mass if gas.molar_mass is not None else 0,
            "density": gas.density_normal_conditions if gas.density_normal_conditions is not None else 0,
            "image_url": get_media_url(gas.gas_image_url, DEFAULT_IMAGE_URL),
            "video_url": get_media_url(gas.gas_video_url, DEFAULT_VIDEO_URL),
            "status": gas.gas_status,
            "likes_count": like_counts.get(gas.id, 0),
        }
        for gas in gases
    ]


async def attach_single_view_data(gas: Gas, db: AsyncSession) -> dict:
    view_gas = (await attach_view_data([gas], db))[0]
    return view_gas


async def get_liked_gas_ids(db: AsyncSession, user_id: int) -> set[int]:
    result = await db.execute(
        select(GasLike.gas_id).where(GasLike.user_id == user_id)
    )

    return set(result.scalars().all())


async def serialize_api_gas(gas: Gas, db: AsyncSession, user_id: int | None) -> dict:
    like_counts = await get_like_counts(db)
    liked_gas_ids = (
        await get_liked_gas_ids(db, user_id)
        if user_id is not None
        else set()
    )

    return {
        "id": gas.id,
        "gas_name": gas.gas_name,
        "gas_formula": gas.gas_formula,
        "short_description": gas.short_description,
        "gas_image_url": get_media_url(gas.gas_image_url, DEFAULT_IMAGE_URL),
        "gas_video_url": get_media_url(gas.gas_video_url, DEFAULT_VIDEO_URL),
        "molar_mass": gas.molar_mass,
        "density_normal_conditions": gas.density_normal_conditions,
        "gas_status": gas.gas_status,
        "likes_count": like_counts.get(gas.id, 0),
        "is_owner": 1 if user_id is not None and gas.creator_id == user_id else 0,
        "is_liked": 1 if gas.id in liked_gas_ids else 0,
    }


@router.get(
    "/api/gases",
    response_model=list[GasListItem],
    summary="Получить список газов",
    description="Возвращает опубликованные газы. Поддерживает фильтрацию по названию через query-параметр search. Доступно гостю.",
)
async def api_get_gases(
    search: str = "",
    db: AsyncSession = Depends(get_db),
    current_user_id: int | None = Depends(get_optional_current_user_id),
):
    stmt = select(Gas).where(Gas.gas_status == "published")

    if search:
        stmt = stmt.where(Gas.gas_name.ilike(f"%{search}%"))

    result = await db.execute(stmt.order_by(Gas.id))
    gases = result.scalars().all()

    return [
        await serialize_api_gas(gas, db, current_user_id)
        for gas in gases
    ]


@router.get(
    "/api/gases/feed",
    response_model=GasFeedItem,
    summary="Получить газ для ленты",
    description="Возвращает опубликованный газ для ленты. Без параметров возвращает первый газ. С gas_id и next=true возвращает следующий опубликованный газ. Доступно гостю.",
)
async def api_get_feed(
    gas_id: int | None = None,
    next: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user_id: int | None = Depends(get_optional_current_user_id),
):
    result = await db.execute(
        select(Gas)
        .where(Gas.gas_status == "published")
        .order_by(Gas.id)
    )
    published_gases = result.scalars().all()

    if not published_gases:
        raise HTTPException(status_code=404, detail="Опубликованные газы не найдены")

    if gas_id is None:
        return await serialize_api_gas(published_gases[0], db, current_user_id)

    gas = None

    for index, current_gas in enumerate(published_gases):
        if current_gas.id == gas_id:
            if next:
                next_index = (index + 1) % len(published_gases)
                gas = published_gases[next_index]
            else:
                gas = current_gas
            break

    if gas is None:
        raise HTTPException(status_code=404, detail="Газ не найден")

    return await serialize_api_gas(gas, db, current_user_id)


# @router.get("/api/gases/feed/{gas_id}", response_model=GasFeedItem)
# async def api_get_feed_by_id(
#     gas_id: int,
#     next: bool = False,
#     db: AsyncSession = Depends(get_db),
# ):
#     current_user_id = get_current_user_id()
#
#     result = await db.execute(
#         select(Gas)
#         .where(Gas.gas_status == "published")
#         .order_by(Gas.id)
#     )
#     published_gases = result.scalars().all()
#
#     gas = None
#
#     for index, current_gas in enumerate(published_gases):
#         if current_gas.id == gas_id:
#             if next:
#                 next_index = (index + 1) % len(published_gases)
#                 gas = published_gases[next_index]
#             else:
#                 gas = current_gas
#             break
#
#     if gas is None:
#         raise HTTPException(status_code=404, detail="Газ не найден")
#
#     return await serialize_api_gas(gas, db, current_user_id)


@router.get(
    "/api/gases/draft",
    response_model=GasDraftResponse,
    summary="Получить черновик газа",
    description="Возвращает черновик текущего авторизованного пользователя. Требует cookie session_id.",
)
async def api_get_draft(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Gas)
        .where(
            Gas.creator_id == current_user_id,
            Gas.gas_status == "draft",
        )
        .order_by(Gas.id)
    )
    draft_gas = result.scalars().first()

    if draft_gas is None:
        raise HTTPException(status_code=404, detail="Черновик не найден")

    return await serialize_api_gas(draft_gas, db, current_user_id)


@router.post(
    "/api/gases",
    response_model=GasDraftResponse,
    summary="Создать газ",
    description="Создает газ в статусе draft и загружает изображение и видео в MinIO. creator_id берется из авторизованной cookie-сессии.",
)
async def api_create_gas(
    gas_name: str = Form(...),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    existing_draft_result = await db.execute(
        select(Gas).where(
            Gas.creator_id == current_user_id,
            Gas.gas_status == "draft",
        )
    )
    existing_draft = existing_draft_result.scalar_one_or_none()

    if existing_draft:
        raise HTTPException(
            status_code=400,
            detail="У пользователя уже есть черновик",
        )

    image_url = upload_file_to_minio(image)
    video_url = upload_file_to_minio(video)

    gas = Gas(
        gas_name=gas_name,
        gas_formula="",
        short_description="",
        gas_status="draft",
        gas_image_url=image_url,
        gas_video_url=video_url,
        molar_mass=None,
        density_normal_conditions=None,
        created_at=datetime.now(),
        formed_at=None,
        creator_id=current_user_id,
    )

    db.add(gas)
    await db.commit()
    await db.refresh(gas)

    return await serialize_api_gas(gas, db, current_user_id)


@router.put(
    "/api/gases/{gas_id}/publish",
    response_model=GasActionResponse,
    summary="Опубликовать газ",
    description="Публикует черновик текущего пользователя. Гость получает 401, чужой газ нельзя опубликовать.",
)
async def api_publish_gas(
    gas_id: int,
    data: GasPublishRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Gas).where(
            Gas.id == gas_id,
            Gas.creator_id == current_user_id,
            Gas.gas_status == "draft",
        )
    )
    gas = result.scalar_one_or_none()

    if gas is None:
        raise HTTPException(
            status_code=404,
            detail="Черновик газа не найден",
        )

    gas.molar_mass = data.molar_mass
    gas.density_normal_conditions = data.density_normal_conditions
    gas.gas_status = "published"
    gas.formed_at = datetime.now()

    await db.commit()

    return {
        "id": gas.id,
        "gas_status": gas.gas_status,
        "message": "Газ опубликован",
    }


@router.delete(
    "/api/gases/{gas_id}",
    response_model=GasActionResponse,
    summary="Удалить газ",
    description="Выполняет soft delete газа текущего пользователя: статус меняется на deleted.",
)
async def api_delete_gas(
    gas_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    result = await db.execute(
        select(Gas).where(
            Gas.id == gas_id,
            Gas.creator_id == current_user_id,
            Gas.gas_status != "deleted",
        )
    )
    gas = result.scalar_one_or_none()

    if gas is None:
        raise HTTPException(
            status_code=404,
            detail="Газ не найден или не принадлежит текущему пользователю",
        )

    gas.gas_status = "deleted"

    await db.commit()

    return {
        "id": gas.id,
        "gas_status": gas.gas_status,
        "message": "Газ логически удален",
    }


@router.post(
    "/api/gases/{gas_id}/like",
    summary="Поставить или убрать лайк",
    description="Ставит или убирает лайк от текущего авторизованного пользователя. value=1 ставит лайк, value=0 убирает.",
)
async def api_set_like(
    gas_id: int,
    data: GasLikeRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if data.value not in (0, 1):
        raise HTTPException(
            status_code=400,
            detail="Поле value должно быть 0 или 1",
        )

    gas_result = await db.execute(
        select(Gas).where(
            Gas.id == gas_id,
            Gas.gas_status == "published",
        )
    )
    gas = gas_result.scalar_one_or_none()

    if gas is None:
        raise HTTPException(status_code=404, detail="Опубликованный газ не найден")

    like_result = await db.execute(
        select(GasLike).where(
            GasLike.user_id == current_user_id,
            GasLike.gas_id == gas_id,
        )
    )
    existing_like = like_result.scalar_one_or_none()

    if data.value == 1 and existing_like is None:
        db.add(
            GasLike(
                user_id=current_user_id,
                gas_id=gas_id,
            )
        )

    if data.value == 0 and existing_like is not None:
        await db.delete(existing_like)

    await db.commit()

    return {
        "gas_id": gas_id,
        "liked": data.value,
        "message": "Лайк обновлен",
    }


@router.post(
    "/api/users/register",
    response_model=UserResponse,
    summary="Зарегистрировать пользователя",
    description="Создает пользователя и сохраняет пароль в виде password_hash.",
)
async def api_register_user(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    existing_user_result = await db.execute(
        select(User).where(User.username == data.username)
    )
    existing_user = existing_user_result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким именем уже существует",
        )

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
    }


@router.post(
    "/api/users/login",
    response_model=AuthStubResponse,
    summary="Аутентифицировать пользователя",
    description="Проверяет логин и пароль, создает сессию в Redis и отправляет session_id в cookie.",
)
async def api_login_user(
    data: AuthStubRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.username == data.username)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Неверное имя пользователя или пароль",
        )

    session_id = await create_session(user.id, user.username)

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )

    return {
        "message": "Аутентификация выполнена",
        "current_user_id": user.id,
    }


@router.post(
    "/api/users/logout",
    response_model=AuthStubResponse,
    summary="Выйти из системы",
    description="Удаляет сессию пользователя из Redis и очищает cookie session_id.",
)
async def api_logout_user(
    request: Request,
    response: Response,
):
    session_id = request.cookies.get("session_id")

    await delete_session(session_id)

    response.delete_cookie("session_id")

    return {
        "message": "Деавторизация выполнена",
        "current_user_id": None,
    }


# @router.get("/")
# async def get_catalog(
#     request: Request,
#     search: str = "",
#     db: AsyncSession = Depends(get_db),
# ):
#     stmt = select(Gas).where(Gas.gas_status == "published")
#
#     if search:
#         stmt = stmt.where(Gas.gas_name.ilike(f"%{search}%"))
#
#     result = await db.execute(stmt.order_by(Gas.id))
#     gases = result.scalars().all()
#
#     return templates.TemplateResponse(
#         request=request,
#         name="gas_catalog.html",
#         context={
#             "gases": await attach_view_data(gases, db),
#             "search": search,
#         },
#     )
#
# @router.get("/feed")
# async def get_feed(request: Request, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(
#         select(Gas)
#         .where(Gas.gas_status == "published")
#         .order_by(Gas.id)
#     )
#
#     first_gas = result.scalars().first()
#
#     if first_gas is None:
#         raise HTTPException(status_code=404, detail="Опубликованные газы не найдены")
#
#     return templates.TemplateResponse(
#         request=request,
#         name="gas_feed.html",
#         context={
#             "gas": await attach_single_view_data(first_gas, db),
#         },
#     )
#
# @router.get("/gas/{gas_id}")
# async def get_gas_detail(
#     request: Request,
#     gas_id: int,
#     next: bool = False,
#     db: AsyncSession = Depends(get_db),
# ):
#     result = await db.execute(
#         select(Gas)
#         .where(Gas.gas_status == "published")
#         .order_by(Gas.id)
#     )
#     published_gases = result.scalars().all()
#
#     gas = None
#
#     for index, current_gas in enumerate(published_gases):
#         if current_gas.id == gas_id:
#             if next:
#                 next_index = (index + 1) % len(published_gases)
#                 gas = published_gases[next_index]
#             else:
#                 gas = current_gas
#             break
#
#     if gas is None:
#         raise HTTPException(status_code=404, detail="Газ не найден")
#
#     return templates.TemplateResponse(
#         request=request,
#         name="gas_feed.html",
#         context={
#             "gas": await attach_single_view_data(gas, db),
#         },
#     )
#
#
# @router.get("/gas_draft")
# async def get_gas_draft(
#     request: Request,
#     db: AsyncSession = Depends(get_db),
# ):
#     result = await db.execute(
#         select(Gas)
#         .where(
#             Gas.creator_id == get_current_user_id(),
#             Gas.gas_status == "draft",
#         )
#         .order_by(Gas.id)
#     )
#     draft_gas = result.scalars().first()
#
#     mixture_molar_mass = 32.00 * 0.60 + 28.01 * 0.40
#
#     return templates.TemplateResponse(
#         request=request,
#         name="gas_draft.html",
#         context={
#             "gas": await attach_single_view_data(draft_gas, db) if draft_gas else None,
#             "mixture_molar_mass": round(mixture_molar_mass, 2),
#         },
#     )
#
#
#
# @router.post("/gas/draft")
# async def create_draft_gas(
#     gas_name: str = Form(...),
#     db: AsyncSession = Depends(get_db),
# ):
#     existing_draft_result = await db.execute(
#         select(Gas).where(
#             Gas.creator_id == get_current_user_id(),
#             Gas.gas_status == "draft",
#         )
#     )
#     existing_draft = existing_draft_result.scalar_one_or_none()
#
#     if existing_draft:
#         return RedirectResponse(url="/gas_draft", status_code=303)
#
#     draft_gas = Gas(
#         gas_name=gas_name,
#         gas_formula="",
#         short_description="",
#         gas_status="draft",
#         gas_image_url=None,
#         gas_video_url=None,
#         molar_mass=None,
#         density_normal_conditions=None,
#         created_at=datetime.now(),
#         formed_at=None,
#         creator_id=get_current_user_id(),
#     )
#
#     db.add(draft_gas)
#     await db.commit()
#
#     return RedirectResponse(url="/gas_draft", status_code=303)
#
#
# @router.post("/gas/{gas_id}/publish")
# async def publish_gas(
#     gas_id: int,
#     gas_formula: str = Form(...),
#     short_description: str = Form(...),
#     molar_mass: float = Form(...),
#     density_normal_conditions: float = Form(...),
#     db: AsyncSession = Depends(get_db),
# ):
#     result = await db.execute(
#         select(Gas).where(
#             Gas.id == gas_id,
#             Gas.creator_id == get_current_user_id(),
#             Gas.gas_status == "draft",
#         )
#     )
#     gas = result.scalar_one_or_none()
#
#     if gas is None:
#         raise HTTPException(status_code=404, detail="Черновик газа не найден")
#
#     gas.gas_formula = gas_formula
#     gas.short_description = short_description
#     gas.molar_mass = molar_mass
#     gas.density_normal_conditions = density_normal_conditions
#     gas.gas_status = "published"
#     gas.formed_at = datetime.now()
#
#     await db.commit()
#
#     return RedirectResponse(url="/", status_code=303)
#
#
# @router.post("/gas/{gas_id}/delete")
# async def delete_gas(
#     gas_id: int,
#     db: AsyncSession = Depends(get_db),
# ):
#     await db.execute(
#         text(
#             """
#             UPDATE gases
#             SET gas_status = 'deleted'
#             WHERE id = :gas_id
#             """
#         ),
#         {"gas_id": gas_id},
#     )
#     await db.commit()
#
#     return RedirectResponse(url="/", status_code=303)
