"""Database module."""
from .models import Base, User, Disciplina, Turma, AlunoTurma, Avaliacao, UserRole
from .connection import engine, SessionLocal, get_db, get_db_context, init_db

__all__ = [
    "Base",
    "User",
    "Disciplina", 
    "Turma",
    "AlunoTurma",
    "Avaliacao",
    "UserRole",
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_context",
    "init_db",
]
