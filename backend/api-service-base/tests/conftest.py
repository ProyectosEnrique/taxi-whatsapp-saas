import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src import fare_service
from src.auth import create_token, hash_password
from src.database import Base, get_db
from src.models import Customer
from src.rate_limit import limiter
from src.routers import customer_rides, payments

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _reset_db():
    """Tablas frescas, caché de tarifas limpia y contador de rate-limit
    reiniciado en cada test — TestClient siempre pega desde la misma IP
    simulada, así que sin esto los tests de register/login de distintos
    tests se acumularían contra el mismo contador."""
    Base.metadata.create_all(bind=engine)
    fare_service.invalidate_cache()
    limiter.reset()
    yield
    fare_service.invalidate_cache()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app():
    """App FastAPI mínima con sólo los routers bajo prueba — evita el
    lifespan de src.main (engine real, tareas en background, webhook
    de Telegram)."""
    test_app = FastAPI()
    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    test_app.include_router(customer_rides.router)
    test_app.include_router(payments.router)
    test_app.dependency_overrides[get_db] = _override_get_db
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def customer(db_session):
    """Cliente de prueba ya persistido + headers de auth listos para usar."""
    customer = Customer(
        phone="+521111111111",
        name="Cliente Test",
        password_hash=hash_password("secret123"),
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    token = create_token(customer.phone, "customer")
    headers = {"Authorization": f"Bearer {token}"}
    return customer, token, headers
