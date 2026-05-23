"""
================================================================================
ADDRESSES ROUTER - Gestión de Direcciones
================================================================================
Endpoints CRUD para direcciones de entrega del usuario
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from ..database import get_db
from ..models.address import Address
from ..models.user import User
from ..schemas.address import AddressCreate, AddressUpdate, AddressResponse
from ..routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get(
    "",
    response_model=List[AddressResponse],
    summary="Listar direcciones del usuario"
)
async def get_addresses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener todas las direcciones guardadas del usuario"""
    logger.info(f"Listando direcciones de usuario: {current_user.id}")

    addresses = db.query(Address).filter(
        Address.user_id == current_user.id
    ).order_by(Address.is_default.desc(), Address.created_at.desc()).all()

    return [AddressResponse.from_orm(addr) for addr in addresses]


@router.post(
    "",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nueva dirección"
)
async def create_address(
    data: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crear una nueva dirección de entrega"""
    logger.info(f"Creando dirección para usuario: {current_user.id}")

    # Si se marca como predeterminada, desmarcar las demás
    if data.is_default:
        db.query(Address).filter(
            Address.user_id == current_user.id,
            Address.is_default == True
        ).update({"is_default": False})

    # Si es la primera dirección, marcarla como predeterminada automáticamente
    existing_count = db.query(Address).filter(
        Address.user_id == current_user.id
    ).count()

    is_default = data.is_default or (existing_count == 0)

    # Crear dirección
    new_address = Address(
        user_id=current_user.id,
        label=data.label,
        street=data.street,
        neighborhood=data.neighborhood,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        country=data.country,
        reference=data.reference,
        latitude=data.latitude,
        longitude=data.longitude,
        is_default=is_default
    )

    db.add(new_address)
    db.commit()
    db.refresh(new_address)

    logger.info(f"Dirección creada: {new_address.id}")

    return AddressResponse.from_orm(new_address)


@router.get(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Obtener una dirección"
)
async def get_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener información de una dirección específica"""
    logger.info(f"Consultando dirección: {address_id}")

    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección no encontrada"
        )

    return AddressResponse.from_orm(address)


@router.put(
    "/{address_id}",
    response_model=AddressResponse,
    summary="Actualizar dirección"
)
async def update_address(
    address_id: int,
    data: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Actualizar una dirección existente"""
    logger.info(f"Actualizando dirección: {address_id}")

    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección no encontrada"
        )

    # Actualizar campos proporcionados
    update_data = data.dict(exclude_unset=True)

    for field, value in update_data.items():
        setattr(address, field, value)

    db.commit()
    db.refresh(address)

    logger.info(f"Dirección actualizada: {address_id}")

    return AddressResponse.from_orm(address)


@router.delete(
    "/{address_id}",
    summary="Eliminar dirección"
)
async def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Eliminar una dirección"""
    logger.info(f"Eliminando dirección: {address_id}")

    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección no encontrada"
        )

    was_default = address.is_default

    db.delete(address)
    db.commit()

    # Si era la predeterminada, marcar otra como predeterminada
    if was_default:
        another_address = db.query(Address).filter(
            Address.user_id == current_user.id
        ).first()

        if another_address:
            another_address.is_default = True
            db.commit()

    logger.info(f"Dirección eliminada: {address_id}")

    return {
        "success": True,
        "message": "Dirección eliminada exitosamente"
    }


@router.post(
    "/{address_id}/set-default",
    response_model=AddressResponse,
    summary="Marcar dirección como predeterminada"
)
async def set_default_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Marcar una dirección como predeterminada"""
    logger.info(f"Marcando dirección como predeterminada: {address_id}")

    address = db.query(Address).filter(
        Address.id == address_id,
        Address.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección no encontrada"
        )

    # Desmarcar todas las demás
    db.query(Address).filter(
        Address.user_id == current_user.id,
        Address.is_default == True
    ).update({"is_default": False})

    # Marcar esta como predeterminada
    address.is_default = True
    db.commit()
    db.refresh(address)

    logger.info(f"Dirección marcada como predeterminada: {address_id}")

    return AddressResponse.from_orm(address)
