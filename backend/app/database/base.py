"""
Declarative base for all ORM models.
Kept separate from session.py to avoid circular imports between
models and the engine/session setup.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
