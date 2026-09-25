import os
import secrets

# Se configuran antes de importar app; nunca se carga el .env del usuario.
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ.pop('DB_HOST', None)
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['JWT_SECRET_KEY'] = secrets.token_hex(32)
os.environ['IA_MODO_DEMO'] = 'true'
os.environ.pop('GROQ_API_KEY', None)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import main, models, auth
from app.database import Base, get_db


@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db, monkeypatch):
    def override_db():
        yield db
    main.app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(main, 'engine', db.get_bind())
    monkeypatch.setattr(main, 'client', None)
    with TestClient(main.app) as client:
        yield client
    main.app.dependency_overrides.clear()


@pytest.fixture
def headers(db):
    db.add(models.Administrador(username='prueba', hashed_password=auth.hash_password('solo-pruebas'), activo=True))
    db.commit()
    return {'Authorization': f'Bearer {auth.crear_access_token({"sub": "prueba"})}'}
