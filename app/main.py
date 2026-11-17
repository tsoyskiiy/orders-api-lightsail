from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models, schemas
from .db import Base, engine, get_db
from .security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Таблицы создаются при старте (db уже healthy благодаря depends_on).
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Orders API", version="1.0", lifespan=lifespan)


@app.get("/health", tags=["service"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "version": app.version}


# ---------- auth / users ----------
@app.post(
    "/auth/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"],
)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    user = models.User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    db.refresh(user)
    return user


@app.post("/auth/token", response_model=schemas.Token, tags=["auth"])
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.scalar(
        select(models.User).where(models.User.email == form.username.lower())
    )
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return schemas.Token(access_token=create_access_token(user.id))


@app.get("/users/me", response_model=schemas.UserOut, tags=["users"])
def me(user: models.User = Depends(get_current_user)):
    return user


# ---------- products ----------
@app.get("/products", response_model=list[schemas.ProductOut], tags=["products"])
def list_products(db: Session = Depends(get_db)):
    return db.scalars(select(models.Product).order_by(models.Product.id)).all()


@app.post(
    "/products",
    response_model=schemas.ProductOut,
    status_code=status.HTTP_201_CREATED,
    tags=["products"],
)
def create_product(
    payload: schemas.ProductCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    product = models.Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


# ---------- orders (только свои) ----------
@app.get("/orders", response_model=list[schemas.OrderOut], tags=["orders"])
def list_orders(
    db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
):
    return db.scalars(
        select(models.Order)
        .where(models.Order.user_id == user.id)
        .order_by(models.Order.id)
    ).all()


@app.post(
    "/orders",
    response_model=schemas.OrderOut,
    status_code=status.HTTP_201_CREATED,
    tags=["orders"],
)
def create_order(
    payload: schemas.OrderCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if db.get(models.Product, payload.product_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    order = models.Order(user_id=user.id, **payload.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


# ---------- documents ----------
@app.get("/documents", response_model=list[schemas.DocumentOut], tags=["documents"])
def list_documents(
    db: Session = Depends(get_db), _: models.User = Depends(get_current_user)
):
    return db.scalars(select(models.Document).order_by(models.Document.id)).all()


@app.post(
    "/documents",
    response_model=schemas.DocumentOut,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
def create_document(
    payload: schemas.DocumentCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    doc = models.Document(**payload.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc
