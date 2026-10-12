from pydantic import BaseModel


class UserRegisterRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str


class AuthStubRequest(BaseModel):
    username: str
    password: str


class AuthStubResponse(BaseModel):
    message: str
    current_user_id: int | None = None
