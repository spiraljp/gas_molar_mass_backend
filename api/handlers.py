from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from collections.abc import Sequence
from db.session import get_db
from models.user import User
from models.gas import Gas
from models.gas_like import GasLike

router = APIRouter()
templates = Jinja2Templates(directory="templates")

DEFAULT_IMAGE_URL = "/static/img/default-gas.png"
DEFAULT_VIDEO_URL = "/static/img/default-gas-video.mp4"
CURRENT_USER_ID = 1


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


@router.get("/")
async def get_catalog(
    request: Request,
    search: str = "",
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Gas).where(Gas.gas_status == "published")

    if search:
        stmt = stmt.where(Gas.gas_name.ilike(f"%{search}%"))

    result = await db.execute(stmt.order_by(Gas.id))
    gases = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "gases": await attach_view_data(gases, db),
            "search": search,
        },
    )


@router.get("/gas/{gas_id}")
async def get_gas_detail(
    request: Request,
    gas_id: int,
    next: bool = False,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Gas)
        .where(Gas.gas_status == "published")
        .order_by(Gas.id)
    )
    published_gases = result.scalars().all()

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

    return templates.TemplateResponse(
        request=request,
        name="gas.html",
        context={
            "gas": await attach_single_view_data(gas, db),
        },
    )


@router.get("/calculation")
async def get_calculation(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Gas)
        .where(
            Gas.creator_id == CURRENT_USER_ID,
            Gas.gas_status == "draft",
        )
        .order_by(Gas.id)
    )
    draft_gas = result.scalars().first()

    mixture_molar_mass = 32.00 * 0.60 + 28.01 * 0.40

    return templates.TemplateResponse(
        request=request,
        name="calculation.html",
        context={
            "gas": await attach_single_view_data(draft_gas, db) if draft_gas else None,
            "mixture_molar_mass": round(mixture_molar_mass, 2),
        },
    )



@router.post("/gas/draft")
async def create_draft_gas(
    gas_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    existing_draft_result = await db.execute(
        select(Gas).where(
            Gas.creator_id == CURRENT_USER_ID,
            Gas.gas_status == "draft",
        )
    )
    existing_draft = existing_draft_result.scalar_one_or_none()

    if existing_draft:
        return RedirectResponse(url="/calculation", status_code=303)

    draft_gas = Gas(
        gas_name=gas_name,
        gas_formula="",
        short_description="",
        gas_status="draft",
        gas_image_url=None,
        gas_video_url=None,
        molar_mass=None,
        density_normal_conditions=None,
        created_at=datetime.now(),
        formed_at=None,
        creator_id=CURRENT_USER_ID,
    )

    db.add(draft_gas)
    await db.commit()

    return RedirectResponse(url="/calculation", status_code=303)


@router.post("/gas/{gas_id}/publish")
async def publish_gas(
    gas_id: int,
    gas_formula: str = Form(...),
    short_description: str = Form(...),
    molar_mass: float = Form(...),
    density_normal_conditions: float = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Gas).where(
            Gas.id == gas_id,
            Gas.creator_id == CURRENT_USER_ID,
            Gas.gas_status == "draft",
        )
    )
    gas = result.scalar_one_or_none()

    if gas is None:
        raise HTTPException(status_code=404, detail="Черновик газа не найден")

    gas.gas_formula = gas_formula
    gas.short_description = short_description
    gas.molar_mass = molar_mass
    gas.density_normal_conditions = density_normal_conditions
    gas.gas_status = "published"
    gas.formed_at = datetime.now()

    await db.commit()

    return RedirectResponse(url="/", status_code=303)


@router.post("/gas/{gas_id}/delete")
async def delete_gas(
    gas_id: int,
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        text(
            """
            UPDATE gases
            SET gas_status = 'deleted'
            WHERE id = :gas_id
            """
        ),
        {"gas_id": gas_id},
    )
    await db.commit()

    return RedirectResponse(url="/", status_code=303)
