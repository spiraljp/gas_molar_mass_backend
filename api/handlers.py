from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates

from data.collections import gases_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_published_gases():
    return [gas for gas in gases_db if gas["status"] == "published"]


@router.get("/")
def get_catalog(request: Request, search: str = ""):
    published_gases = get_published_gases()

    if search:
        published_gases = [
            gas
            for gas in published_gases
            if search.lower() in gas["title"].lower()
        ]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "gases": published_gases,
            "search": search,
        },
    )


@router.get("/gas/{gas_id}")
def get_gas_detail(request: Request, gas_id: int, next: bool = False):
    published_gases = get_published_gases()

    gas = next_gas = None

    for index, current_gas in enumerate(published_gases):
        if current_gas["id"] == gas_id:
            if next:
                next_index = (index + 1) % len(published_gases)
                next_gas = published_gases[next_index]
                gas = next_gas
            else:
                gas = current_gas
            break

    if gas is None:
        raise HTTPException(status_code=404, detail="Газ не найден")

    return templates.TemplateResponse(
        request=request,
        name="gas.html",
        context={
            "gas": gas,
        },
    )


@router.get("/calculation")
def get_calculation(request: Request):
    draft_gas = next((gas for gas in gases_db if gas["status"] == "draft"), None)

    if draft_gas is None:
        raise HTTPException(status_code=404, detail="Черновик газа не найден")

    mixture_molar_mass = 32.00 * 0.60 + 28.01 * 0.40

    return templates.TemplateResponse(
        request=request,
        name="calculation.html",
        context={
            "gas": draft_gas,
            "mixture_molar_mass": round(mixture_molar_mass, 2),
        },
    )
