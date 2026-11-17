from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import EMBEDDING_DIM


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    full_name: str = ""
    password: str = Field(min_length=8, max_length=128)


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(gt=0)


class ProductOut(ORM):
    id: int
    name: str
    price: float


class OrderCreate(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


class OrderOut(ORM):
    id: int
    user_id: int
    product_id: int
    quantity: int
    created_at: datetime


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = ""
    embedding: list[float] | None = Field(
        default=None, min_length=EMBEDDING_DIM, max_length=EMBEDDING_DIM
    )


class DocumentOut(ORM):
    id: int
    title: str
    content: str
    created_at: datetime
