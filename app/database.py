import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if os.getenv("DB_HOST"):
    DATABASE_URL = URL.create(
        "postgresql+psycopg2", username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"], host=os.environ["DB_HOST"],
        database=os.environ["POSTGRES_DB"],
    )
if not DATABASE_URL:
    raise RuntimeError("Falta DATABASE_URL en tu archivo .env")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """
    Dependencia de FastAPI para obtener una sesión de DB por request.
    Centralizada aquí para no repetirla en main.py, auth.py, etc.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
