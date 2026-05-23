"""
================================================================================
SOCKET.IO SERVER - Real-time Communication
================================================================================
Servidor Socket.IO para actualizaciones en tiempo real de pedidos
================================================================================
"""

import socketio
import logging
from typing import Optional, Dict, Set
from datetime import datetime

logger = logging.getLogger(__name__)

# Crear servidor Socket.IO con CORS
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # En producción, especificar dominios permitidos
    logger=True,
    engineio_logger=False
)

# Socket.IO app ASGI
socket_app = socketio.ASGIApp(
    sio,
    socketio_path='socket.io'
)


# ==============================================================================
# STORAGE - Usuarios conectados por order_id
# ==============================================================================

# Estructura: {order_id: {sid1, sid2, ...}}
order_rooms: Dict[str, Set[str]] = {}

# Estructura: {sid: user_info}
connected_users: Dict[str, dict] = {}


# ==============================================================================
# CONNECTION EVENTS
# ==============================================================================

@sio.event
async def connect(sid, environ, auth):
    """
    Cliente conectado.

    auth debería contener:
    - user_id: ID del usuario
    - tenant_id: ID del tenant
    - token: JWT token (opcional para validación)
    """
    logger.info(f"Cliente conectado: {sid}")

    # Guardar info del usuario
    if auth:
        connected_users[sid] = {
            "user_id": auth.get("user_id"),
            "tenant_id": auth.get("tenant_id"),
            "connected_at": datetime.now().isoformat()
        }
        logger.info(f"Usuario autenticado: {auth.get('user_id')} (tenant: {auth.get('tenant_id')})")

    await sio.emit('connected', {
        'status': 'connected',
        'sid': sid,
        'message': 'Conectado al servidor de tiempo real'
    }, to=sid)


@sio.event
async def disconnect(sid):
    """Cliente desconectado"""
    logger.info(f"Cliente desconectado: {sid}")

    # Remover de todos los rooms
    for order_id, sids in order_rooms.items():
        if sid in sids:
            sids.remove(sid)
            logger.info(f"Removido de room: {order_id}")

    # Limpiar rooms vacíos
    empty_rooms = [oid for oid, sids in order_rooms.items() if len(sids) == 0]
    for oid in empty_rooms:
        del order_rooms[oid]

    # Remover info del usuario
    if sid in connected_users:
        del connected_users[sid]


# ==============================================================================
# ORDER TRACKING EVENTS
# ==============================================================================

@sio.event
async def join_order(sid, data):
    """
    Unirse al room de un pedido para recibir actualizaciones.

    data:
    - order_id: ID del pedido a seguir
    """
    order_id = data.get('order_id')

    if not order_id:
        await sio.emit('error', {
            'message': 'order_id es requerido'
        }, to=sid)
        return

    logger.info(f"Cliente {sid} uniéndose al pedido {order_id}")

    # Agregar al room
    if order_id not in order_rooms:
        order_rooms[order_id] = set()
    order_rooms[order_id].add(sid)

    await sio.emit('joined_order', {
        'order_id': order_id,
        'message': f'Ahora recibirás actualizaciones del pedido {order_id}'
    }, to=sid)


@sio.event
async def leave_order(sid, data):
    """
    Salir del room de un pedido.

    data:
    - order_id: ID del pedido
    """
    order_id = data.get('order_id')

    if not order_id:
        return

    logger.info(f"Cliente {sid} saliendo del pedido {order_id}")

    # Remover del room
    if order_id in order_rooms and sid in order_rooms[order_id]:
        order_rooms[order_id].remove(sid)

        # Limpiar room si está vacío
        if len(order_rooms[order_id]) == 0:
            del order_rooms[order_id]

        await sio.emit('left_order', {
            'order_id': order_id,
            'message': f'Ya no recibirás actualizaciones del pedido {order_id}'
        }, to=sid)


@sio.event
async def ping(sid, data):
    """Ping para verificar conexión"""
    await sio.emit('pong', {'timestamp': datetime.now().isoformat()}, to=sid)


# ==============================================================================
# BROADCAST FUNCTIONS (LLAMADAS DESDE LA API)
# ==============================================================================

async def broadcast_order_update(order_id: str, update_data: dict):
    """
    Enviar actualización de pedido a todos los clientes suscritos.

    Args:
        order_id: ID del pedido
        update_data: Datos de la actualización (status, estimated_time, etc.)
    """
    if order_id not in order_rooms:
        logger.info(f"No hay clientes suscritos al pedido {order_id}")
        return

    logger.info(f"Enviando actualización del pedido {order_id} a {len(order_rooms[order_id])} clientes")

    # Enviar a todos los clientes del room
    for sid in order_rooms[order_id]:
        await sio.emit('order_update', {
            'order_id': order_id,
            'timestamp': datetime.now().isoformat(),
            **update_data
        }, to=sid)


async def broadcast_order_status_change(order_id: str, old_status: str, new_status: str, additional_data: Optional[dict] = None):
    """
    Notificar cambio de estado de pedido.

    Args:
        order_id: ID del pedido
        old_status: Estado anterior
        new_status: Nuevo estado
        additional_data: Datos adicionales opcionales
    """
    data = {
        'event_type': 'status_change',
        'old_status': old_status,
        'new_status': new_status
    }

    if additional_data:
        data.update(additional_data)

    await broadcast_order_update(order_id, data)


async def broadcast_order_notification(order_id: str, notification_type: str, message: str, data: Optional[dict] = None):
    """
    Enviar notificación general sobre un pedido.

    Args:
        order_id: ID del pedido
        notification_type: Tipo (info, warning, success, error)
        message: Mensaje de la notificación
        data: Datos adicionales opcionales
    """
    payload = {
        'event_type': 'notification',
        'notification_type': notification_type,
        'message': message
    }

    if data:
        payload.update(data)

    await broadcast_order_update(order_id, payload)


async def broadcast_delivery_location(order_id: str, latitude: float, longitude: float, driver_name: Optional[str] = None):
    """
    Enviar ubicación en tiempo real del repartidor.

    Args:
        order_id: ID del pedido
        latitude: Latitud actual
        longitude: Longitud actual
        driver_name: Nombre del repartidor (opcional)
    """
    data = {
        'event_type': 'delivery_location',
        'location': {
            'latitude': latitude,
            'longitude': longitude
        }
    }

    if driver_name:
        data['driver_name'] = driver_name

    await broadcast_order_update(order_id, data)


async def broadcast_estimated_time(order_id: str, estimated_minutes: int):
    """
    Actualizar tiempo estimado de entrega.

    Args:
        order_id: ID del pedido
        estimated_minutes: Minutos estimados
    """
    await broadcast_order_update(order_id, {
        'event_type': 'estimated_time',
        'estimated_minutes': estimated_minutes,
        'estimated_time': f"{estimated_minutes} minutos"
    })


# ==============================================================================
# ADMIN EVENTS (Para dashboard de administración)
# ==============================================================================

@sio.event
async def join_admin_room(sid, data):
    """
    Unirse al room de administración para recibir todas las actualizaciones.

    Requiere autenticación de administrador.
    """
    tenant_id = data.get('tenant_id')

    if not tenant_id:
        await sio.emit('error', {'message': 'tenant_id requerido'}, to=sid)
        return

    logger.info(f"Admin {sid} uniéndose a room de tenant {tenant_id}")

    # En producción, verificar que el usuario es admin
    room_name = f"admin_{tenant_id}"
    await sio.enter_room(sid, room_name)

    await sio.emit('joined_admin_room', {
        'tenant_id': tenant_id,
        'message': 'Conectado a panel de administración'
    }, to=sid)


async def broadcast_new_order(tenant_id: str, order_data: dict):
    """
    Notificar a administradores sobre nuevo pedido.

    Args:
        tenant_id: ID del tenant
        order_data: Datos del pedido
    """
    room_name = f"admin_{tenant_id}"

    await sio.emit('new_order', {
        'event_type': 'new_order',
        'timestamp': datetime.now().isoformat(),
        'order': order_data
    }, room=room_name)


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

def get_connected_count() -> int:
    """Obtener cantidad de clientes conectados"""
    return len(connected_users)


def get_order_subscribers(order_id: str) -> int:
    """Obtener cantidad de clientes suscritos a un pedido"""
    return len(order_rooms.get(order_id, set()))


def get_stats() -> dict:
    """Obtener estadísticas del servidor Socket.IO"""
    return {
        "connected_clients": len(connected_users),
        "active_orders": len(order_rooms),
        "total_subscriptions": sum(len(sids) for sids in order_rooms.values())
    }


# ==============================================================================
# LOGGER HELPERS
# ==============================================================================

logger.info("Socket.IO server initialized")
