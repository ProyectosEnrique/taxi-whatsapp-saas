"""
Script para inicializar datos demo del servicio de taxi

Carga conductores, vehículos, clientes y códigos promocionales de ejemplo
para poder probar el sistema sin necesidad de datos reales.

Uso:
    python scripts/init_taxi_demo.py
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Agregar path del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.taxi_models import (
    Driver, Vehicle, Customer, PromoCode,
    DriverStatus, VehicleType, PaymentMethod
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def load_demo_data():
    """
    Carga los datos demo desde el archivo JSON
    """
    config_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'config',
        'taxi_demo_data.json'
    )

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def init_database(db_url: str = None):
    """
    Inicializa la conexión a la base de datos
    """
    if db_url is None:
        db_url = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:password@localhost:5432/whatsapp_saas'
        )

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    return engine, session


def create_drivers_and_vehicles(session, demo_data):
    """
    Crea conductores y sus vehículos
    """
    tenant_id = demo_data['tenant_id']
    drivers_data = demo_data['drivers']

    print(f"\n📍 Creando {len(drivers_data)} conductores...")

    for driver_data in drivers_data:
        # Crear conductor
        driver = Driver(
            driver_id=driver_data['driver_id'],
            tenant_id=tenant_id,
            name=driver_data['name'],
            phone=driver_data['phone'],
            email=driver_data.get('email'),
            license_number=driver_data['license_number'],
            status=DriverStatus[driver_data['status'].upper()],
            current_lat=driver_data['current_location']['lat'],
            current_lon=driver_data['current_location']['lon'],
            last_location_update=datetime.now(),
            rating=driver_data['rating'],
            total_rides=driver_data['total_rides'],
            total_rides_completed=driver_data['total_rides'],
            acceptance_rate=driver_data['acceptance_rate'],
            active=True,
            available_for_rides=(driver_data['status'] == 'available'),
            last_active_at=datetime.now()
        )

        # Crear vehículo del conductor
        vehicle_data = driver_data['vehicle']
        vehicle = Vehicle(
            vehicle_id=f"vehicle_{driver_data['driver_id'][-3:]}",
            driver_id=driver_data['driver_id'],
            tenant_id=tenant_id,
            vehicle_type=VehicleType[vehicle_data['type'].upper()],
            brand=vehicle_data['brand'],
            model=vehicle_data['model'],
            year=vehicle_data['year'],
            color=vehicle_data['color'],
            plates=vehicle_data['plates'],
            passenger_capacity=vehicle_data['passenger_capacity'],
            luggage_capacity=vehicle_data.get('luggage_capacity', 2),
            active=True,
            verified=True
        )

        session.add(driver)
        session.add(vehicle)

        print(f"  ✅ {driver.name} - {vehicle.brand} {vehicle.model} ({vehicle.plates})")

    session.commit()
    print(f"✅ {len(drivers_data)} conductores creados exitosamente")


def create_customers(session, demo_data):
    """
    Crea clientes demo
    """
    tenant_id = demo_data['tenant_id']
    customers_data = demo_data['customers']

    print(f"\n👥 Creando {len(customers_data)} clientes...")

    for customer_data in customers_data:
        customer = Customer(
            customer_id=customer_data['customer_id'],
            tenant_id=tenant_id,
            phone=customer_data['phone'],
            name=customer_data['name'],
            customer_type=customer_data['customer_type'],
            total_rides=customer_data['total_rides'],
            total_rides_completed=customer_data['total_rides'],
            loyalty_points=customer_data.get('loyalty_points', 0),
            saved_addresses=customer_data.get('saved_addresses', []),
            active=True
        )

        session.add(customer)
        print(f"  ✅ {customer.name} ({customer.customer_type}) - {customer.total_rides} viajes")

    session.commit()
    print(f"✅ {len(customers_data)} clientes creados exitosamente")


def create_promo_codes(session, demo_data):
    """
    Crea códigos promocionales
    """
    tenant_id = demo_data['tenant_id']
    promo_codes_data = demo_data['promo_codes']

    print(f"\n🎟️ Creando {len(promo_codes_data)} códigos promocionales...")

    for promo_data in promo_codes_data:
        valid_until = datetime.strptime(promo_data['valid_until'], '%Y-%m-%d')

        promo_code = PromoCode(
            promo_code_id=f"promo_{promo_data['code'].lower()}",
            tenant_id=tenant_id,
            code=promo_data['code'],
            discount_type=promo_data['discount_type'],
            discount_value=promo_data['discount_value'],
            max_discount=promo_data.get('max_discount'),
            min_fare=promo_data.get('min_fare', 0.0),
            usage_limit=promo_data.get('usage_limit'),
            usage_limit_per_customer=promo_data.get('usage_limit_per_customer', 1),
            times_used=0,
            valid_from=datetime.now(),
            valid_until=valid_until,
            active=promo_data['active'],
            min_distance_km=promo_data.get('min_distance_km'),
            description=promo_data['description']
        )

        session.add(promo_code)
        print(f"  ✅ {promo_code.code} - {promo_code.description}")

    session.commit()
    print(f"✅ {len(promo_codes_data)} códigos promocionales creados exitosamente")


def verify_data(session, tenant_id):
    """
    Verifica que los datos se hayan creado correctamente
    """
    print("\n🔍 Verificando datos creados...")

    drivers_count = session.query(Driver).filter_by(tenant_id=tenant_id).count()
    vehicles_count = session.query(Vehicle).filter_by(tenant_id=tenant_id).count()
    customers_count = session.query(Customer).filter_by(tenant_id=tenant_id).count()
    promos_count = session.query(PromoCode).filter_by(tenant_id=tenant_id).count()

    print(f"\n📊 Resumen:")
    print(f"  • Conductores: {drivers_count}")
    print(f"  • Vehículos: {vehicles_count}")
    print(f"  • Clientes: {customers_count}")
    print(f"  • Códigos promo: {promos_count}")

    # Verificar conductores disponibles
    available_drivers = session.query(Driver).filter_by(
        tenant_id=tenant_id,
        status=DriverStatus.AVAILABLE
    ).count()

    print(f"\n✅ Conductores disponibles: {available_drivers}")

    return drivers_count > 0


def main():
    """
    Función principal
    """
    print("=" * 60)
    print("🚕 INICIALIZACIÓN DE DATOS DEMO - SERVICIO DE TAXI")
    print("=" * 60)

    try:
        # Cargar datos demo
        demo_data = load_demo_data()
        tenant_id = demo_data['tenant_id']

        print(f"\n📦 Cargando datos para tenant: {tenant_id}")

        # Conectar a BD
        print("\n🔌 Conectando a base de datos...")
        engine, session = init_database()
        print("✅ Conexión exitosa")

        # Crear tablas si no existen
        print("\n📋 Verificando tablas...")
        from src.models.taxi_models import Base
        Base.metadata.create_all(engine)
        print("✅ Tablas verificadas")

        # Limpiar datos existentes (solo en demo)
        print(f"\n🗑️ Limpiando datos existentes de {tenant_id}...")
        session.query(PromoCode).filter_by(tenant_id=tenant_id).delete()
        session.query(Vehicle).filter_by(tenant_id=tenant_id).delete()
        session.query(Driver).filter_by(tenant_id=tenant_id).delete()
        session.query(Customer).filter_by(tenant_id=tenant_id).delete()
        session.commit()
        print("✅ Datos anteriores eliminados")

        # Crear datos nuevos
        create_drivers_and_vehicles(session, demo_data)
        create_customers(session, demo_data)
        create_promo_codes(session, demo_data)

        # Verificar
        if verify_data(session, tenant_id):
            print("\n" + "=" * 60)
            print("🎉 INICIALIZACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 60)
            print("\n📝 Próximos pasos:")
            print("  1. Configura GOOGLE_MAPS_API_KEY en tu .env")
            print("  2. Inicia el servidor: python run_v2.py")
            print("  3. Envía un mensaje por WhatsApp: 'Necesito taxi'")
            print("\n💡 Números de prueba:")
            print("  • WhatsApp del servicio: +5215500001111")
            print("  • Cliente demo: +5215533333001")
            print("  • Conductor demo: +5215522222001")
        else:
            print("\n❌ Error: No se pudieron crear los datos")
            sys.exit(1)

    except FileNotFoundError:
        print("\n❌ Error: No se encontró el archivo taxi_demo_data.json")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'session' in locals():
            session.close()


if __name__ == "__main__":
    main()
