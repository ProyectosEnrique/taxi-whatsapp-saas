"""
================================================================================
AUTH ROUTER - Autenticación y Gestión de Usuarios
================================================================================
Endpoints para registro, login, y gestión de cuenta
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import logging
import jwt
import bcrypt

from ..database import get_db
from ..models.user import User
from ..schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
    UpdateProfileRequest,
    ChangePasswordRequest
)
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 días


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def hash_password(password: str) -> str:
    """Hashear contraseña con bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crear JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decodificar JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Obtener usuario actual desde JWT token"""
    token = credentials.credentials
    payload = decode_token(token)

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )

    return user


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.post(
    "/register",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario"
)
async def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Registrar un nuevo usuario.

    Crea la cuenta del usuario y devuelve un token JWT para login automático.
    """
    logger.info(f"Registro de usuario: {data.email}")

    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )

    # Verificar si el teléfono ya existe
    existing_phone = db.query(User).filter(User.phone == data.phone).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El teléfono ya está registrado"
        )

    # Crear usuario
    hashed_pwd = hash_password(data.password)

    new_user = User(
        tenant_id=data.tenant_id,
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=hashed_pwd,
        is_active=True,
        is_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Usuario creado: {new_user.id}")

    # Crear token JWT
    access_token = create_access_token(
        data={"user_id": new_user.id, "tenant_id": new_user.tenant_id}
    )

    return LoginResponse(
        success=True,
        access_token=access_token,
        token_type="bearer",
        user=new_user.to_dict()
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Iniciar sesión"
)
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Iniciar sesión con email y contraseña.

    Devuelve un token JWT para autenticación en requests posteriores.
    """
    logger.info(f"Login attempt: {data.email}")

    # Buscar usuario
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    # Verificar contraseña
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos"
        )

    # Verificar que esté activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )

    # Verificar tenant_id si se proporciona
    if data.tenant_id and user.tenant_id != data.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no pertenece a este tenant"
        )

    # Actualizar last_login
    user.last_login = datetime.utcnow()
    db.commit()

    logger.info(f"Login exitoso: {user.id}")

    # Crear token JWT
    access_token = create_access_token(
        data={"user_id": user.id, "tenant_id": user.tenant_id}
    )

    return LoginResponse(
        success=True,
        access_token=access_token,
        token_type="bearer",
        user=user.to_dict()
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener perfil del usuario actual"
)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Obtener información del perfil del usuario autenticado"""
    return UserResponse.from_orm(current_user)


@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Actualizar perfil del usuario"
)
async def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar información del perfil del usuario.

    Solo puede actualizar: nombre y teléfono
    """
    logger.info(f"Actualizando perfil: {current_user.id}")

    # Actualizar campos
    if data.name is not None:
        current_user.name = data.name

    if data.phone is not None:
        # Verificar que el teléfono no esté en uso por otro usuario
        existing = db.query(User).filter(
            User.phone == data.phone,
            User.id != current_user.id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El teléfono ya está en uso"
            )

        current_user.phone = data.phone

    db.commit()
    db.refresh(current_user)

    logger.info(f"Perfil actualizado: {current_user.id}")

    return UserResponse.from_orm(current_user)


@router.post(
    "/change-password",
    summary="Cambiar contraseña"
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cambiar la contraseña del usuario.

    Requiere la contraseña actual para confirmar la identidad.
    """
    logger.info(f"Cambio de contraseña: {current_user.id}")

    # Verificar contraseña actual
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña actual incorrecta"
        )

    # Actualizar contraseña
    current_user.password_hash = hash_password(data.new_password)
    db.commit()

    logger.info(f"Contraseña actualizada: {current_user.id}")

    return {
        "success": True,
        "message": "Contraseña actualizada exitosamente"
    }


@router.post(
    "/logout",
    summary="Cerrar sesión"
)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Cerrar sesión (endpoint informativo).

    En JWT, el logout es del lado del cliente (eliminar el token).
    Este endpoint solo sirve para logging.
    """
    logger.info(f"Logout: {current_user.id}")

    return {
        "success": True,
        "message": "Sesión cerrada. Elimina el token del lado del cliente."
    }
