"""
Database models for the School Grades system.
Defines all SQLAlchemy models according to the data model specification.
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Enum, ForeignKey, 
    Table, UniqueConstraint, create_engine
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(str, PyEnum):
    """User roles enum."""
    STUDENT = "student"
    TEACHER = "teacher"


class User(Base):
    """
    Users table - stores students and teachers.
    
    Attributes:
        id: Unique identifier
        name: User's full name
        role: Either 'student' or 'teacher'
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    role = Column(Enum("student", "teacher", name="user_role"), nullable=False)
    
    # Relationships
    turmas = relationship("AlunoTurma", back_populates="user")
    avaliacoes = relationship("Avaliacao", back_populates="user", foreign_keys="Avaliacao.user_id")
    updated_avaliacoes = relationship("Avaliacao", back_populates="updated_by_user", foreign_keys="Avaliacao.updated_by")
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', role='{self.role}')>"


class Disciplina(Base):
    """
    Disciplinas (subjects/courses) table.
    
    Attributes:
        id: Unique identifier
        name: Subject name (e.g., "Mathematics", "Portuguese")
    """
    __tablename__ = "disciplinas"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    
    # Relationships
    avaliacoes = relationship("Avaliacao", back_populates="disciplina")
    
    def __repr__(self):
        return f"<Disciplina(id={self.id}, name='{self.name}')>"


class Turma(Base):
    """
    Turmas (classes/groups) table.
    
    Attributes:
        id: Unique identifier
        name: Class name (e.g., "10A", "11B")
    """
    __tablename__ = "turmas"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    
    # Relationships
    alunos = relationship("AlunoTurma", back_populates="turma")
    avaliacoes = relationship("Avaliacao", back_populates="turma")
    
    def __repr__(self):
        return f"<Turma(id={self.id}, name='{self.name}')>"


class AlunoTurma(Base):
    """
    Association table linking students to their classes.
    Supports students being in multiple classes.
    
    Attributes:
        user_id: Foreign key to users table
        turma_id: Foreign key to turmas table
    """
    __tablename__ = "alunos_turmas"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    turma_id = Column(Integer, ForeignKey("turmas.id", ondelete="CASCADE"), primary_key=True)
    
    # Relationships
    user = relationship("User", back_populates="turmas")
    turma = relationship("Turma", back_populates="alunos")
    
    def __repr__(self):
        return f"<AlunoTurma(user_id={self.user_id}, turma_id={self.turma_id})>"


class Avaliacao(Base):
    """
    Avaliacoes (evaluations/grades) table.
    Stores all grades with full audit trail.
    
    Attributes:
        id: Unique identifier
        user_id: Student who received the grade
        disciplina_id: Subject of the evaluation
        turma_id: Class context for the evaluation
        modulo: Module identifier (e.g., "Módulo 3", "Capítulo 2")
        descricao: Description (e.g., "Teste 1", "Projeto", "Ficha A")
        valor: Grade value (float, typically 0-20 or 0-100)
        date: Date of the evaluation
        updated_by: Teacher who last updated this grade
        updated_at: Timestamp of last update
    """
    __tablename__ = "avaliacoes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    disciplina_id = Column(Integer, ForeignKey("disciplinas.id", ondelete="CASCADE"), nullable=False)
    turma_id = Column(Integer, ForeignKey("turmas.id", ondelete="CASCADE"), nullable=False)
    modulo = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=False)
    valor = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False, default=func.now())
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="avaliacoes", foreign_keys=[user_id])
    disciplina = relationship("Disciplina", back_populates="avaliacoes")
    turma = relationship("Turma", back_populates="avaliacoes")
    updated_by_user = relationship("User", back_populates="updated_avaliacoes", foreign_keys=[updated_by])
    
    def __repr__(self):
        return f"<Avaliacao(id={self.id}, user_id={self.user_id}, disciplina_id={self.disciplina_id}, valor={self.valor})>"
    
    def to_dict(self):
        """Convert evaluation to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "student_name": self.user.name if self.user else None,
            "disciplina_id": self.disciplina_id,
            "disciplina_name": self.disciplina.name if self.disciplina else None,
            "turma_id": self.turma_id,
            "turma_name": self.turma.name if self.turma else None,
            "modulo": self.modulo,
            "descricao": self.descricao,
            "valor": self.valor,
            "date": self.date.isoformat() if self.date else None,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
