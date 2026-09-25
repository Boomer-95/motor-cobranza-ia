import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models
from .database import get_db

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "Falta JWT_SECRET_KEY en tu .env. Genera una con: "
        "python -c \"import secrets; print(secrets.token_hex(32))\""
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # sesión válida por 1 hora

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def hash_password(password_plano: str) -> str:
    if len(password_plano.encode("utf-8")) > 72:
        raise ValueError("La contraseña no debe superar 72 bytes UTF-8.")
    return pwd_context.hash(password_plano)


def verificar_password(password_plano: str, password_hash: str) -> bool:
    if len(password_plano.encode("utf-8")) > 72:
        return False
    try:
        return pwd_context.verify(password_plano, password_hash)
    except (ValueError, TypeError):
        return False


def crear_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_admin_actual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Administrador:
    """
    Dependencia para proteger endpoints: se agrega como
    `admin: models.Administrador = Depends(get_admin_actual)`
    a cualquier ruta que solo el administrador autenticado deba ver.
    """
    credenciales_invalidas = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la sesión. Inicia sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise credenciales_invalidas
    except JWTError:
        raise credenciales_invalidas

    admin = db.query(models.Administrador).filter(
        models.Administrador.username == username
    ).first()
    if admin is None or not admin.activo:
        raise credenciales_invalidas

    return admin
