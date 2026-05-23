"""
Database Models for Taxi Service

Modelos de base de datos para el servicio de taxi:
- Driver (conductores)
- Ride (viajes)
- Customer (clientes)
- Vehicle (vehículos)
- PromoCode (códigos promocionales)
- Rating (calificaciones)
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum, Time
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class DriverStatus(enum.Enum):
    """Estados del conductor"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ON_BREAK = "on_break"


class RideStatus(enum.Enum):
    """Estados del viaje"""
    REQUESTED = "requested"
    ASSIGNED = "assigned"
    DRIVER_ARRIVING = "driver_arriving"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED_BY_CUSTOMER = "cancelled_by_customer"
    CANCELLED_BY_DRIVER = "cancelled_by_driver"
    CANCELLED_NO_DRIVER = "cancelled_no_driver"


class PaymentMethod(enum.Enum):
    """Métodos de pago"""
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    WALLET = "wallet"
    CORPORATE = "corporate"


class VehicleType(enum.Enum):
    """Tipos de vehículo"""
    SEDAN = "sedan"
    SUV = "suv"
    VAN = "van"
    LUXURY = "luxury"
    MOTORCYCLE = "motorcycle"


class Driver(Base):
    """
    Modelo de Conductor
    """
    __tablename__ = "drivers"

    # Identificación
    driver_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)

    # Información personal
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False, unique=True, index=True)
    email = Column(String(100))
    profile_photo_url = Column(String(255))

    # Documentación
    license_number = Column(String(50), nullable=False)
    license_expiry = Column(DateTime)
    background_check_status = Column(String(20), default="pending")  # pending, approved, rejected
    background_check_date = Column(DateTime)

    # Estado y ubicación
    status = Column(SQLEnum(DriverStatus), default=DriverStatus.OFFLINE, nullable=False, index=True)
    current_lat = Column(Float)
    current_lon = Column(Float)
    last_location_update = Column(DateTime)
    heading = Column(Float)  # Dirección en grados (0-360)

    # Métricas
    rating = Column(Float, default=5.0)
    total_rides = Column(Integer, default=0)
    total_rides_completed = Column(Integer, default=0)
    total_rides_cancelled = Column(Integer, default=0)
    acceptance_rate = Column(Float, default=1.0)  # 0.0 - 1.0
    cancellation_rate = Column(Float, default=0.0)
    total_earnings = Column(Float, default=0.0)

    # Configuración
    active = Column(Boolean, default=True)
    available_for_rides = Column(Boolean, default=True)
    max_radius_km = Column(Float, default=15.0)  # Radio máximo de operación

    # Metadatos
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_active_at = Column(DateTime)

    # Relaciones
    vehicles = relationship("Vehicle", back_populates="driver")
    rides = relationship("Ride", back_populates="driver")
    ratings_received = relationship("Rating", back_populates="driver")
    schedules = relationship("DriverSchedule", back_populates="driver")

    def to_dict(self):
        return {
            "driver_id": self.driver_id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "phone": self.phone,
            "status": self.status.value if self.status else None,
            "current_location": {
                "lat": self.current_lat,
                "lon": self.current_lon
            } if self.current_lat and self.current_lon else None,
            "rating": self.rating,
            "total_rides": self.total_rides,
            "acceptance_rate": self.acceptance_rate,
            "active": self.active
        }


class Vehicle(Base):
    """
    Modelo de Vehículo
    """
    __tablename__ = "vehicles"

    # Identificación
    vehicle_id = Column(String(50), primary_key=True)
    driver_id = Column(String(50), ForeignKey("drivers.driver_id"), nullable=False)
    tenant_id = Column(String(50), nullable=False, index=True)

    # Información del vehículo
    vehicle_type = Column(SQLEnum(VehicleType), nullable=False)
    brand = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    color = Column(String(30), nullable=False)
    plates = Column(String(20), nullable=False, unique=True)

    # Documentación
    registration_number = Column(String(50))
    insurance_policy = Column(String(100))
    insurance_expiry = Column(DateTime)

    # Características
    passenger_capacity = Column(Integer, default=4)
    luggage_capacity = Column(Integer, default=2)
    wheelchair_accessible = Column(Boolean, default=False)
    pet_friendly = Column(Boolean, default=False)
    air_conditioning = Column(Boolean, default=True)

    # Estado
    active = Column(Boolean, default=True)
    verified = Column(Boolean, default=False)

    # Metadatos
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relaciones
    driver = relationship("Driver", back_populates="vehicles")

    def to_dict(self):
        return {
            "vehicle_id": self.vehicle_id,
            "type": self.vehicle_type.value if self.vehicle_type else None,
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "color": self.color,
            "plates": self.plates,
            "passenger_capacity": self.passenger_capacity
        }


class Customer(Base):
    """
    Modelo de Cliente (usuario de taxi)
    """
    __tablename__ = "customers"

    # Identificación
    customer_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    phone = Column(String(20), nullable=False, unique=True, index=True)

    # Información personal
    name = Column(String(100))
    email = Column(String(100))
    profile_photo_url = Column(String(255))

    # Preferencias
    preferred_payment_method = Column(SQLEnum(PaymentMethod), default=PaymentMethod.CASH)
    preferred_vehicle_type = Column(SQLEnum(VehicleType))
    saved_addresses = Column(JSON)  # [{"label": "Casa", "address": "...", "lat": ..., "lon": ...}]

    # Métricas
    total_rides = Column(Integer, default=0)
    total_rides_completed = Column(Integer, default=0)
    total_rides_cancelled = Column(Integer, default=0)
    total_spent = Column(Float, default=0.0)
    average_rating_given = Column(Float, default=5.0)

    # Segmentación
    customer_type = Column(String(20), default="new")  # new, frequent, vip, corporate
    loyalty_points = Column(Integer, default=0)

    # Estado
    active = Column(Boolean, default=True)
    blocked = Column(Boolean, default=False)

    # Metadatos
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    last_ride_at = Column(DateTime)

    # Relaciones
    rides = relationship("Ride", back_populates="customer")
    ratings_given = relationship("Rating", back_populates="customer")

    def to_dict(self):
        return {
            "customer_id": self.customer_id,
            "phone": self.phone,
            "name": self.name,
            "customer_type": self.customer_type,
            "total_rides": self.total_rides,
            "loyalty_points": self.loyalty_points
        }


class Ride(Base):
    """
    Modelo de Viaje
    """
    __tablename__ = "rides"

    # Identificación
    ride_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    driver_id = Column(String(50), ForeignKey("drivers.driver_id"))

    # Ubicaciones
    origin_address = Column(Text, nullable=False)
    origin_lat = Column(Float, nullable=False)
    origin_lon = Column(Float, nullable=False)

    destination_address = Column(Text, nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lon = Column(Float, nullable=False)

    # Información del viaje
    distance_km = Column(Float)
    duration_minutes = Column(Float)
    actual_distance_km = Column(Float)
    actual_duration_minutes = Column(Float)

    # Tarifa
    fare_breakdown = Column(JSON)  # Desglose completo de la tarifa
    base_fare = Column(Float)
    distance_charge = Column(Float)
    time_charge = Column(Float)
    surge_charge = Column(Float, default=0.0)
    special_charges = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    total_fare = Column(Float, nullable=False)
    currency = Column(String(3), default="MXN")

    # Pago
    payment_method = Column(SQLEnum(PaymentMethod), default=PaymentMethod.CASH)
    paid = Column(Boolean, default=False)
    payment_transaction_id = Column(String(100))

    # Estado
    status = Column(SQLEnum(RideStatus), default=RideStatus.REQUESTED, nullable=False, index=True)

    # Tiempos
    requested_at = Column(DateTime, default=datetime.now, nullable=False)
    scheduled_for = Column(DateTime)  # Para viajes programados
    assigned_at = Column(DateTime)
    driver_arrived_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)

    # Condiciones especiales
    special_conditions = Column(JSON)  # {"airport_pickup": true, "extra_passengers": 2, ...}
    notes = Column(Text)  # Notas del cliente

    # Calificaciones
    customer_rating = Column(Float)  # Calificación del conductor por el cliente
    driver_rating = Column(Float)  # Calificación del cliente por el conductor

    # Tracking
    route_polyline = Column(Text)  # Ruta planificada
    actual_route_points = Column(JSON)  # [[lat, lon, timestamp], ...]

    # Metadatos
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relaciones
    customer = relationship("Customer", back_populates="rides")
    driver = relationship("Driver", back_populates="rides")

    def to_dict(self):
        return {
            "ride_id": self.ride_id,
            "status": self.status.value if self.status else None,
            "origin": {
                "address": self.origin_address,
                "lat": self.origin_lat,
                "lon": self.origin_lon
            },
            "destination": {
                "address": self.destination_address,
                "lat": self.destination_lat,
                "lon": self.destination_lon
            },
            "distance_km": self.distance_km,
            "duration_minutes": self.duration_minutes,
            "total_fare": self.total_fare,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "driver_id": self.driver_id,
            "customer_id": self.customer_id,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None
        }


class Rating(Base):
    """
    Modelo de Calificación
    """
    __tablename__ = "ratings"

    # Identificación
    rating_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    ride_id = Column(String(50), ForeignKey("rides.ride_id"), nullable=False)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    driver_id = Column(String(50), ForeignKey("drivers.driver_id"), nullable=False)

    # Calificación
    rating = Column(Float, nullable=False)  # 1.0 - 5.0
    review = Column(Text)

    # Aspectos evaluados (opcional)
    punctuality_rating = Column(Float)
    cleanliness_rating = Column(Float)
    driving_rating = Column(Float)
    communication_rating = Column(Float)

    # Tipo
    rating_type = Column(String(20), nullable=False)  # "customer_to_driver" o "driver_to_customer"

    # Metadatos
    created_at = Column(DateTime, default=datetime.now)

    # Relaciones
    customer = relationship("Customer", back_populates="ratings_given")
    driver = relationship("Driver", back_populates="ratings_received")

    def to_dict(self):
        return {
            "rating_id": self.rating_id,
            "ride_id": self.ride_id,
            "rating": self.rating,
            "review": self.review,
            "rating_type": self.rating_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class PromoCode(Base):
    """
    Modelo de Código Promocional
    """
    __tablename__ = "promo_codes"

    # Identificación
    promo_code_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    code = Column(String(20), nullable=False, unique=True, index=True)

    # Configuración
    discount_type = Column(String(20), nullable=False)  # "percentage", "fixed_amount"
    discount_value = Column(Float, nullable=False)
    max_discount = Column(Float)  # Descuento máximo en pesos
    min_fare = Column(Float, default=0.0)  # Tarifa mínima para aplicar

    # Restricciones
    usage_limit = Column(Integer)  # Límite total de usos
    usage_limit_per_customer = Column(Integer, default=1)
    times_used = Column(Integer, default=0)

    # Validez
    valid_from = Column(DateTime, default=datetime.now)
    valid_until = Column(DateTime)
    active = Column(Boolean, default=True)

    # Restricciones adicionales
    applicable_vehicle_types = Column(JSON)  # ["sedan", "suv"]
    applicable_customer_types = Column(JSON)  # ["new", "frequent"]
    min_distance_km = Column(Float)

    # Descripción
    description = Column(Text)

    # Metadatos
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(String(50))  # admin user id

    def to_dict(self):
        return {
            "promo_code_id": self.promo_code_id,
            "code": self.code,
            "discount_type": self.discount_type,
            "discount_value": self.discount_value,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "active": self.active,
            "times_used": self.times_used
        }


class DriverSchedule(Base):
    """
    Horarios de trabajo configurados por el conductor
    """
    __tablename__ = "driver_schedules"

    # Identificación
    schedule_id = Column(String(50), primary_key=True)
    driver_id = Column(String(50), ForeignKey("drivers.driver_id"), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)

    # Configuración del turno
    day_of_week = Column(Integer, nullable=False)  # 0=Lunes, 6=Domingo
    shift_type = Column(String(20), nullable=False)  # morning/afternoon/night/flexible
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    # Descansos
    break_start = Column(Time, nullable=True)
    break_end = Column(Time, nullable=True)

    # Estado
    is_active = Column(Boolean, default=True)
    is_recurring = Column(Boolean, default=True)  # Si se repite cada semana

    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relación
    driver = relationship("Driver", back_populates="schedules")

    def to_dict(self):
        return {
            "schedule_id": self.schedule_id,
            "driver_id": self.driver_id,
            "tenant_id": self.tenant_id,
            "day_of_week": self.day_of_week,
            "shift_type": self.shift_type,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "break_start": self.break_start.strftime("%H:%M") if self.break_start else None,
            "break_end": self.break_end.strftime("%H:%M") if self.break_end else None,
            "is_active": self.is_active,
            "is_recurring": self.is_recurring,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# Función helper para crear todas las tablas
def create_tables(engine):
    """
    Crea todas las tablas en la base de datos
    """
    Base.metadata.create_all(engine)
    print("✅ All taxi tables created successfully")


# Función helper para borrar todas las tablas (desarrollo)
def drop_tables(engine):
    """
    Borra todas las tablas (usar solo en desarrollo)
    """
    Base.metadata.drop_all(engine)
    print("🗑️ All taxi tables dropped")
