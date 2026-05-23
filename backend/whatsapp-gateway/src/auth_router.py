# ============================================================================
# AUTH ROUTER - Endpoints de Autenticación
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from src.database import get_db
from src.orm_models import UserORM
from src.models_multitenant import (
    UserLogin, TokenResponse, User, UserPasswordChange,
    UserUpdate, SuccessResponse
)
from src.auth import (
    authenticate_user, create_access_token,
    get_current_user, hash_password
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# ============================================================================
# LOGIN
# ============================================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login y obtener token JWT.

    Credenciales:
    - email: Email del usuario
    - password: Password

    Retorna:
    - access_token: JWT token
    - user: Datos del usuario
    """
    # Autenticar
    user = authenticate_user(db, credentials.email, credentials.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Crear token
    access_token = create_access_token(
        user_id=user.user_id,
        role=user.role,
        restaurant_id=user.restaurant_id
    )

    # Actualizar last_login
    user.last_login_at = datetime.utcnow()
    db.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=User.from_orm(user)
    )


# ============================================================================
# GET CURRENT USER (ME)
# ============================================================================

@router.get("/me", response_model=User)
async def get_me(
    current_user: UserORM = Depends(get_current_user)
):
    """
    Obtener información del usuario actual.

    Requiere token JWT en header:
    Authorization: Bearer <token>
    """
    return User.from_orm(current_user)


# ============================================================================
# UPDATE PROFILE
# ============================================================================

@router.patch("/me", response_model=User)
async def update_profile(
    user_update: UserUpdate,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Actualizar perfil del usuario actual.

    Solo puede actualizar:
    - full_name
    - phone
    """
    update_data = user_update.dict(exclude_unset=True)

    for field, value in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return User.from_orm(current_user)


# ============================================================================
# CHANGE PASSWORD
# ============================================================================

@router.post("/password", response_model=SuccessResponse)
async def change_password(
    password_change: UserPasswordChange,
    current_user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cambiar contraseña del usuario actual.

    Requiere:
    - current_password: Contraseña actual
    - new_password: Nueva contraseña (mínimo 8 caracteres)
    """
    from src.auth import verify_password

    # Verificar contraseña actual
    if not verify_password(password_change.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Actualizar contraseña
    current_user.password_hash = hash_password(password_change.new_password)
    db.commit()

    return SuccessResponse(
        success=True,
        message="Password changed successfully"
    )


# ============================================================================
# REQUEST PASSWORD RESET
# ============================================================================

@router.post("/password-reset", response_model=SuccessResponse)
async def request_password_reset(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Solicitar reset de contraseña.

    Envía email con token de reset (TODO: implementar envío de email).
    Por ahora solo retorna el token.
    """
    import uuid
    from datetime import timedelta

    user = db.query(UserORM).filter(UserORM.email == email).first()

    if not user:
        # Por seguridad, no revelar si el email existe
        return SuccessResponse(
            success=True,
            message="If the email exists, a reset link will be sent"
        )

    # Generar token
    reset_token = uuid.uuid4().hex
    user.password_reset_token = reset_token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=24)

    db.commit()

    # TODO: Enviar email con el link
    # send_email(
    #     to=user.email,
    #     subject="Reset your password",
    #     body=f"Reset token: {reset_token}"
    # )

    return SuccessResponse(
        success=True,
        message="If the email exists, a reset link will be sent",
        data={"reset_token": reset_token}  # Solo para desarrollo
    )


# ============================================================================
# CONFIRM PASSWORD RESET
# ============================================================================

@router.post("/password-reset/confirm", response_model=SuccessResponse)
async def confirm_password_reset(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """
    Confirmar reset de contraseña con token.

    Parámetros:
    - token: Token recibido por email
    - new_password: Nueva contraseña
    """
    user = db.query(UserORM).filter(
        UserORM.password_reset_token == token
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Verificar expiración
    if user.password_reset_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )

    # Actualizar contraseña
    user.password_hash = hash_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None

    db.commit()

    return SuccessResponse(
        success=True,
        message="Password reset successfully"
    )


# ============================================================================
# LOGOUT (Client-side)
# ============================================================================

@router.post("/logout", response_model=SuccessResponse)
async def logout():
    """
    Logout (solo client-side).

    Con JWT, el logout se maneja en el cliente eliminando el token.
    Este endpoint es solo informativo.
    """
    return SuccessResponse(
        success=True,
        message="Logged out successfully. Please delete the token from client."
    )
