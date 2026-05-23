"""JWT helpers — tokens para clientes y conductores."""
import os
from datetime import datetime, timezone, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from .models import Customer, Driver

SECRET_KEY = os.getenv("JWT_SECRET", "changeme")
ALGORITHM  = "HS256"
TOKEN_TTL_HOURS = 72

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer      = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    return jwt.encode(
        {"sub": subject, "role": role, "exp": expire},
        SECRET_KEY, algorithm=ALGORITHM,
    )


def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")


def get_current_customer(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Customer:
    if not creds:
        raise HTTPException(status_code=401, detail="Token requerido")
    payload = _decode(creds.credentials)
    if payload.get("role") != "customer":
        raise HTTPException(status_code=403, detail="No autorizado")
    customer = db.query(Customer).filter(Customer.phone == payload["sub"]).first()
    if not customer or not customer.is_active:
        raise HTTPException(status_code=401, detail="Cliente no encontrado")
    return customer


def get_current_driver(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Driver:
    if not creds:
        raise HTTPException(status_code=401, detail="Token requerido")
    payload = _decode(creds.credentials)
    if payload.get("role") != "driver":
        raise HTTPException(status_code=403, detail="No autorizado")
    driver = db.query(Driver).filter(Driver.phone == payload["sub"]).first()
    if not driver or not driver.is_active:
        raise HTTPException(status_code=401, detail="Conductor no encontrado")
    return driver
