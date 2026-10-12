from pydantic import BaseModel


class GasListItem(BaseModel):
    id: int
    gas_name: str
    gas_formula: str
    short_description: str
    gas_image_url: str | None
    gas_video_url: str | None
    molar_mass: float | None
    density_normal_conditions: float | None
    likes_count: int
    is_owner: int


class GasFeedItem(BaseModel):
    id: int
    gas_name: str
    gas_formula: str
    short_description: str
    gas_video_url: str | None
    molar_mass: float | None
    density_normal_conditions: float | None
    likes_count: int
    is_liked: int


class GasDraftResponse(BaseModel):
    id: int
    gas_name: str
    gas_formula: str
    short_description: str
    gas_image_url: str | None
    gas_video_url: str | None
    molar_mass: float | None
    density_normal_conditions: float | None
    gas_status: str

class GasPublishRequest(BaseModel):
    molar_mass: float
    density_normal_conditions: float


class GasLikeRequest(BaseModel):
    value: int


class GasActionResponse(BaseModel):
    id: int
    gas_status: str
    message: str
