"""
================================================================================
DRIVER SCHEDULE API ROUTES
================================================================================
Endpoints REST para gestionar horarios de conductores de taxi.

Endpoints:
- GET    /api/driver/schedule - Obtener horarios del conductor
- POST   /api/driver/schedule - Crear horario nuevo
- POST   /api/driver/schedule/bulk - Crear múltiples horarios
- PUT    /api/driver/schedule/<schedule_id> - Actualizar horario
- DELETE /api/driver/schedule/<schedule_id> - Eliminar horario
- GET    /api/driver/schedule/templates - Obtener plantillas de turnos
================================================================================
"""

import logging
from datetime import time
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Importar modelo
try:
    from src.models.taxi_models import DriverSchedule
    from src.database.connection import get_session
    MODELS_AVAILABLE = True
except ImportError as e:
    MODELS_AVAILABLE = False
    import_error = str(e)

logger = logging.getLogger(__name__)

# Blueprint
driver_schedule_bp = Blueprint('driver_schedule', __name__, url_prefix='/api/driver/schedule')


# ==============================================================================
# SHIFT TEMPLATES
# ==============================================================================
SHIFT_TEMPLATES = {
    "morning": {
        "name": "Turno Matutino",
        "shift_type": "morning",
        "start_time": "06:00",
        "end_time": "14:00",
        "break_start": "10:00",
        "break_end": "10:30",
        "description": "Turno de mañana, ideal para inicio del día"
    },
    "afternoon": {
        "name": "Turno Vespertino",
        "shift_type": "afternoon",
        "start_time": "14:00",
        "end_time": "22:00",
        "break_start": "18:00",
        "break_end": "18:30",
        "description": "Turno de tarde, alta demanda"
    },
    "night": {
        "name": "Turno Nocturno",
        "shift_type": "night",
        "start_time": "22:00",
        "end_time": "06:00",
        "break_start": "02:00",
        "break_end": "02:30",
        "description": "Turno de noche, servicio 24/7"
    },
    "flexible": {
        "name": "Turno Flexible",
        "shift_type": "flexible",
        "start_time": "08:00",
        "end_time": "20:00",
        "break_start": "13:00",
        "break_end": "14:00",
        "description": "Horario flexible, configurable"
    }
}


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def parse_time(time_str):
    """Convertir string HH:MM a objeto time"""
    if not time_str:
        return None
    try:
        hour, minute = map(int, time_str.split(':'))
        return time(hour, minute)
    except:
        return None


def validate_schedule_data(data):
    """Validar datos de horario"""
    required_fields = ['day_of_week', 'shift_type', 'start_time', 'end_time']

    for field in required_fields:
        if field not in data:
            return False, f"Campo requerido: {field}"

    # Validar day_of_week
    if not isinstance(data['day_of_week'], int) or data['day_of_week'] < 0 or data['day_of_week'] > 6:
        return False, "day_of_week debe ser un número entre 0 (Lunes) y 6 (Domingo)"

    # Validar shift_type
    valid_shifts = ['morning', 'afternoon', 'night', 'flexible']
    if data['shift_type'] not in valid_shifts:
        return False, f"shift_type debe ser uno de: {', '.join(valid_shifts)}"

    # Validar tiempos
    if not parse_time(data['start_time']):
        return False, "start_time debe estar en formato HH:MM"

    if not parse_time(data['end_time']):
        return False, "end_time debe estar en formato HH:MM"

    # Validar break (opcional)
    if 'break_start' in data and data['break_start']:
        if not parse_time(data['break_start']):
            return False, "break_start debe estar en formato HH:MM"

    if 'break_end' in data and data['break_end']:
        if not parse_time(data['break_end']):
            return False, "break_end debe estar en formato HH:MM"

    return True, None


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@driver_schedule_bp.route('/health', methods=['GET'])
def health():
    """Health check del servicio de horarios"""
    return jsonify({
        'status': 'healthy' if MODELS_AVAILABLE else 'unavailable',
        'models_available': MODELS_AVAILABLE,
        'message': 'Driver Schedule API ready' if MODELS_AVAILABLE else import_error
    })


@driver_schedule_bp.route('/templates', methods=['GET'])
def get_templates():
    """
    Obtener plantillas de turnos predefinidos

    Returns:
        200: Lista de plantillas disponibles
    """
    return jsonify({
        'success': True,
        'templates': SHIFT_TEMPLATES
    })


@driver_schedule_bp.route('', methods=['GET'])
def get_schedules():
    """
    Obtener todos los horarios de un conductor

    Query params:
        - driver_id (required): ID del conductor
        - tenant_id (required): ID del tenant
        - day_of_week (optional): Filtrar por día de la semana
        - is_active (optional): Filtrar por estado activo

    Returns:
        200: Lista de horarios
        400: Parámetros faltantes
        500: Error del servidor
    """
    if not MODELS_AVAILABLE:
        return jsonify({'success': False, 'error': 'Models not available'}), 500

    # Obtener parámetros
    driver_id = request.args.get('driver_id')
    tenant_id = request.args.get('tenant_id')
    day_of_week = request.args.get('day_of_week', type=int)
    is_active = request.args.get('is_active', type=lambda v: v.lower() == 'true')

    # Validar parámetros requeridos
    if not driver_id or not tenant_id:
        return jsonify({
            'success': False,
            'error': 'driver_id y tenant_id son requeridos'
        }), 400

    try:
        db: Session = get_session()

        # Construir query
        filters = [
            DriverSchedule.driver_id == driver_id,
            DriverSchedule.tenant_id == tenant_id
        ]

        if day_of_week is not None:
            filters.append(DriverSchedule.day_of_week == day_of_week)

        if is_active is not None:
            filters.append(DriverSchedule.is_active == is_active)

        # Ejecutar query
        schedules = db.query(DriverSchedule).filter(and_(*filters)).all()

        return jsonify({
            'success': True,
            'schedules': [schedule.to_dict() for schedule in schedules]
        })

    except Exception as e:
        logger.error(f"Error obteniendo horarios: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@driver_schedule_bp.route('', methods=['POST'])
def create_schedule():
    """
    Crear un nuevo horario

    Body (JSON):
        - driver_id (required): ID del conductor
        - tenant_id (required): ID del tenant
        - day_of_week (required): Día de la semana (0-6)
        - shift_type (required): Tipo de turno (morning/afternoon/night/flexible)
        - start_time (required): Hora de inicio (HH:MM)
        - end_time (required): Hora de fin (HH:MM)
        - break_start (optional): Hora de inicio de descanso (HH:MM)
        - break_end (optional): Hora de fin de descanso (HH:MM)
        - is_active (optional): Estado activo (default: true)
        - is_recurring (optional): Si se repite cada semana (default: true)

    Returns:
        201: Horario creado exitosamente
        400: Datos inválidos
        500: Error del servidor
    """
    if not MODELS_AVAILABLE:
        return jsonify({'success': False, 'error': 'Models not available'}), 500

    data = request.get_json()

    # Validar datos requeridos
    if 'driver_id' not in data or 'tenant_id' not in data:
        return jsonify({
            'success': False,
            'error': 'driver_id y tenant_id son requeridos'
        }), 400

    # Validar datos del horario
    is_valid, error_msg = validate_schedule_data(data)
    if not is_valid:
        return jsonify({'success': False, 'error': error_msg}), 400

    try:
        db: Session = get_session()

        # Generar ID único
        import uuid
        schedule_id = f"schedule_{uuid.uuid4().hex[:12]}"

        # Crear horario
        schedule = DriverSchedule(
            schedule_id=schedule_id,
            driver_id=data['driver_id'],
            tenant_id=data['tenant_id'],
            day_of_week=data['day_of_week'],
            shift_type=data['shift_type'],
            start_time=parse_time(data['start_time']),
            end_time=parse_time(data['end_time']),
            break_start=parse_time(data.get('break_start')),
            break_end=parse_time(data.get('break_end')),
            is_active=data.get('is_active', True),
            is_recurring=data.get('is_recurring', True)
        )

        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        return jsonify({
            'success': True,
            'message': 'Horario creado exitosamente',
            'schedule': schedule.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creando horario: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@driver_schedule_bp.route('/bulk', methods=['POST'])
def create_bulk_schedules():
    """
    Crear múltiples horarios de una vez

    Body (JSON):
        - driver_id (required): ID del conductor
        - tenant_id (required): ID del tenant
        - schedules (required): Lista de horarios a crear

    Returns:
        201: Horarios creados exitosamente
        400: Datos inválidos
        500: Error del servidor
    """
    if not MODELS_AVAILABLE:
        return jsonify({'success': False, 'error': 'Models not available'}), 500

    data = request.get_json()

    # Validar datos requeridos
    if 'driver_id' not in data or 'tenant_id' not in data or 'schedules' not in data:
        return jsonify({
            'success': False,
            'error': 'driver_id, tenant_id y schedules son requeridos'
        }), 400

    if not isinstance(data['schedules'], list) or len(data['schedules']) == 0:
        return jsonify({
            'success': False,
            'error': 'schedules debe ser una lista no vacía'
        }), 400

    try:
        db: Session = get_session()
        created_schedules = []

        for schedule_data in data['schedules']:
            # Validar cada horario
            is_valid, error_msg = validate_schedule_data(schedule_data)
            if not is_valid:
                db.rollback()
                return jsonify({'success': False, 'error': f"Error en horario: {error_msg}"}), 400

            # Generar ID único
            import uuid
            schedule_id = f"schedule_{uuid.uuid4().hex[:12]}"

            # Crear horario
            schedule = DriverSchedule(
                schedule_id=schedule_id,
                driver_id=data['driver_id'],
                tenant_id=data['tenant_id'],
                day_of_week=schedule_data['day_of_week'],
                shift_type=schedule_data['shift_type'],
                start_time=parse_time(schedule_data['start_time']),
                end_time=parse_time(schedule_data['end_time']),
                break_start=parse_time(schedule_data.get('break_start')),
                break_end=parse_time(schedule_data.get('break_end')),
                is_active=schedule_data.get('is_active', True),
                is_recurring=schedule_data.get('is_recurring', True)
            )

            db.add(schedule)
            created_schedules.append(schedule)

        db.commit()

        # Refresh todos los objetos
        for schedule in created_schedules:
            db.refresh(schedule)

        return jsonify({
            'success': True,
            'message': f'{len(created_schedules)} horarios creados exitosamente',
            'schedules': [schedule.to_dict() for schedule in created_schedules]
        }), 201

    except Exception as e:
        logger.error(f"Error creando horarios en bulk: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@driver_schedule_bp.route('/<schedule_id>', methods=['PUT'])
def update_schedule(schedule_id):
    """
    Actualizar un horario existente

    Path params:
        - schedule_id: ID del horario a actualizar

    Body (JSON): Campos a actualizar (todos opcionales excepto tenant_id)
        - tenant_id (required): ID del tenant (validación)
        - day_of_week: Día de la semana (0-6)
        - shift_type: Tipo de turno
        - start_time: Hora de inicio (HH:MM)
        - end_time: Hora de fin (HH:MM)
        - break_start: Hora de inicio de descanso (HH:MM)
        - break_end: Hora de fin de descanso (HH:MM)
        - is_active: Estado activo
        - is_recurring: Si se repite cada semana

    Returns:
        200: Horario actualizado exitosamente
        400: Datos inválidos
        404: Horario no encontrado
        500: Error del servidor
    """
    if not MODELS_AVAILABLE:
        return jsonify({'success': False, 'error': 'Models not available'}), 500

    data = request.get_json()

    # Validar tenant_id
    if 'tenant_id' not in data:
        return jsonify({
            'success': False,
            'error': 'tenant_id es requerido para validación'
        }), 400

    try:
        db: Session = get_session()

        # Buscar horario
        schedule = db.query(DriverSchedule).filter(
            and_(
                DriverSchedule.schedule_id == schedule_id,
                DriverSchedule.tenant_id == data['tenant_id']
            )
        ).first()

        if not schedule:
            return jsonify({
                'success': False,
                'error': 'Horario no encontrado'
            }), 404

        # Actualizar campos
        if 'day_of_week' in data:
            if not isinstance(data['day_of_week'], int) or data['day_of_week'] < 0 or data['day_of_week'] > 6:
                return jsonify({'success': False, 'error': 'day_of_week inválido'}), 400
            schedule.day_of_week = data['day_of_week']

        if 'shift_type' in data:
            valid_shifts = ['morning', 'afternoon', 'night', 'flexible']
            if data['shift_type'] not in valid_shifts:
                return jsonify({'success': False, 'error': 'shift_type inválido'}), 400
            schedule.shift_type = data['shift_type']

        if 'start_time' in data:
            start_time = parse_time(data['start_time'])
            if not start_time:
                return jsonify({'success': False, 'error': 'start_time inválido'}), 400
            schedule.start_time = start_time

        if 'end_time' in data:
            end_time = parse_time(data['end_time'])
            if not end_time:
                return jsonify({'success': False, 'error': 'end_time inválido'}), 400
            schedule.end_time = end_time

        if 'break_start' in data:
            schedule.break_start = parse_time(data['break_start'])

        if 'break_end' in data:
            schedule.break_end = parse_time(data['break_end'])

        if 'is_active' in data:
            schedule.is_active = bool(data['is_active'])

        if 'is_recurring' in data:
            schedule.is_recurring = bool(data['is_recurring'])

        db.commit()
        db.refresh(schedule)

        return jsonify({
            'success': True,
            'message': 'Horario actualizado exitosamente',
            'schedule': schedule.to_dict()
        })

    except Exception as e:
        logger.error(f"Error actualizando horario: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


@driver_schedule_bp.route('/<schedule_id>', methods=['DELETE'])
def delete_schedule(schedule_id):
    """
    Eliminar un horario

    Path params:
        - schedule_id: ID del horario a eliminar

    Query params:
        - tenant_id (required): ID del tenant (validación)

    Returns:
        200: Horario eliminado exitosamente
        400: Parámetros faltantes
        404: Horario no encontrado
        500: Error del servidor
    """
    if not MODELS_AVAILABLE:
        return jsonify({'success': False, 'error': 'Models not available'}), 500

    tenant_id = request.args.get('tenant_id')

    if not tenant_id:
        return jsonify({
            'success': False,
            'error': 'tenant_id es requerido'
        }), 400

    try:
        db: Session = get_session()

        # Buscar horario
        schedule = db.query(DriverSchedule).filter(
            and_(
                DriverSchedule.schedule_id == schedule_id,
                DriverSchedule.tenant_id == tenant_id
            )
        ).first()

        if not schedule:
            return jsonify({
                'success': False,
                'error': 'Horario no encontrado'
            }), 404

        db.delete(schedule)
        db.commit()

        return jsonify({
            'success': True,
            'message': 'Horario eliminado exitosamente'
        })

    except Exception as e:
        logger.error(f"Error eliminando horario: {e}")
        db.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        db.close()


def register_driver_schedule_routes(app):
    """Registrar las rutas en la aplicación Flask"""
    app.register_blueprint(driver_schedule_bp)
    logger.info("Driver Schedule routes registered")
