# ============================================================================
# AUTH - Sistema de Autenticación JWT
# ============================================================================

import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.database import get_db
from src.orm_models import UserORM, RestaurantORM
from src.models_multitenant import TokenData, UserRole

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer security
security = HTTPBearer()


# ============================================================================
# PASSWORD UTILITIES
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash de password con bcrypt
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar password
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT UTILITIES
# ============================================================================

def create_access_token(
    user_id: str,
    role: str,
    restaurant_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crear JWT access token
    """
    to_encode = {
        "user_id": user_id,
        "role": role,
        "restaurant_id": restaurant_id
    }

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    Decodificar y validar JWT token
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        role: str = payload.get("role")
        restaurant_id: Optional[str] = payload.get("restaurant_id")
        exp: int = payload.get("exp")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

        return TokenData(
            user_id=user_id,
            role=UserRole(role),
            restaurant_id=restaurant_id,
            exp=datetime.fromtimestamp(exp)
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserORM:
    """
    Dependency para obtener usuario actual desde JWT token.

    Usage:
        @app.get("/me")
        def get_me(current_user: UserORM = Depends(get_current_user)):
            return current_user
    """
    token = credentials.credentials
    token_data = decode_access_token(token)

    # Buscar usuario en DB
    user = db.query(UserORM).filter(
        UserORM.user_id == token_data.user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    return user


async def get_current_active_user(
    current_user: UserORM = Depends(get_current_user)
) -> UserORM:
    """
    Dependency para obtener usuario activo.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# ============================================================================
# AUTHORIZATION DEPENDENCIES
# ============================================================================

class RoleChecker:
    """
    Dependency class para verificar roles.

    Usage:
        allow_owner = RoleChecker([UserRole.OWNER, UserRole.SUPER_ADMIN])

        @app.get("/products")
        def get_products(current_user: UserORM = Depends(allow_owner)):
            ...
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: UserORM = Depends(get_current_user)) -> UserORM:
        if UserRole(current_user.role) not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return current_user


# Definir checkers comunes
allow_super_admin = RoleChecker([UserRole.SUPER_ADMIN])
allow_owner = RoleChecker([UserRole.OWNER, UserRole.SUPER_ADMIN])
allow_manager = RoleChecker([UserRole.OWNER, UserRole.MANAGER, UserRole.SUPER_ADMIN])
allow_all_staff = RoleChecker([UserRole.OWNER, UserRole.MANAGER, UserRole.EMPLOYEE, UserRole.SUPER_ADMIN])


# ============================================================================
# RESTAURANT ACCESS CHECKER
# ============================================================================

async def check_restaurant_access(
    restaurant_id: str,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> RestaurantORM:
    """
    Verificar que el usuario tenga acceso al restaurante.

    - Super admin: acceso a todos
    - Owner/Manager/Employee: solo su restaurante

    Usage:
        @app.get("/restaurants/{restaurant_id}/products")
        def get_products(
            restaurant_id: str,
            restaurant: RestaurantORM = Depends(check_restaurant_access)
        ):
            ...
    """

    # Super admin tiene acceso a todo
    if current_user.role == UserRole.SUPER_ADMIN.value:
        restaurant = db.query(RestaurantORM).filter(
            RestaurantORM.restaurant_id == restaurant_id
        ).first()

        if not restaurant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Restaurant not found"
            )

        return restaurant

    # Otros usuarios solo acceden a su restaurante
    if current_user.restaurant_id != restaurant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this restaurant"
        )

    restaurant = db.query(RestaurantORM).filter(
        RestaurantORM.restaurant_id == restaurant_id
    ).first()

    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found"
        )

    return restaurant


# ============================================================================
# AUTHENTICATION HELPERS
# ============================================================================

def authenticate_user(db: Session, email: str, password: str) -> Optional[UserORM]:
    """
    Autenticar usuario con email y password.
    Retorna el usuario si las credenciales son válidas, None si no.
    """
    user = db.query(UserORM).filter(UserORM.email == email).first()

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def generate_user_id() -> str:
    """
    Generar user_id único
    """
    import uuid
    return f"user_{uuid.uuid4().hex[:12]}"


def generate_restaurant_id() -> str:
    """
    Generar restaurant_id único
    """
    import uuid
    return f"rest_{uuid.uuid4().hex[:12]}"
