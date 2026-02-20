"""
Grade writing tools for the School Grades system.
All write operations are restricted to teachers only.

CRITICAL: NO DELETE OPERATIONS EXIST BY DESIGN
"""
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from database import Avaliacao, User, Disciplina, Turma
from .authorization import AuthorizationService
from .exceptions import ValidationError, FeatureNotAvailableError


def add_grade(
    db: Session,
    teacher_id: int,
    student_id: int,
    disciplina_id: int,
    turma_id: int,
    modulo: str,
    descricao: str,
    valor: float,
    date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Add a new grade for a student.
    
    AUTHORIZATION: Teacher only.
    
    Args:
        db: Database session
        teacher_id: ID of the teacher adding the grade
        student_id: ID of the student receiving the grade
        disciplina_id: ID of the subject
        turma_id: ID of the class
        modulo: Module identifier (e.g., "Módulo 3")
        descricao: Description (e.g., "Teste 1")
        valor: Grade value
        date: Date of evaluation (defaults to now)
        
    Returns:
        Created evaluation data
        
    Raises:
        TeacherOnlyError: If requester is not a teacher
        ValidationError: If validation fails
    """
    auth_service = AuthorizationService(db)
    
    # ENFORCEMENT: Only teachers can add grades
    auth_service.enforce_teacher_only(teacher_id, "add_grade")
    
    # Validate student exists and is actually a student
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise ValidationError(f"Student with id {student_id} not found", "student_id")
    if student.role != "student":
        raise ValidationError(f"User {student_id} is not a student", "student_id")
    
    # Validate disciplina exists
    disciplina = db.query(Disciplina).filter(Disciplina.id == disciplina_id).first()
    if not disciplina:
        raise ValidationError(f"Disciplina with id {disciplina_id} not found", "disciplina_id")
    
    # Validate turma exists
    turma = db.query(Turma).filter(Turma.id == turma_id).first()
    if not turma:
        raise ValidationError(f"Turma with id {turma_id} not found", "turma_id")
    
    # Validate valor
    if valor < 0 or valor > 20:
        raise ValidationError("Grade value must be between 0 and 20", "valor")
    
    # Create evaluation
    avaliacao = Avaliacao(
        user_id=student_id,
        disciplina_id=disciplina_id,
        turma_id=turma_id,
        modulo=modulo,
        descricao=descricao,
        valor=valor,
        date=date or datetime.now(),
        updated_by=teacher_id
    )
    
    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)
    
    return {
        "success": True,
        "message": f"Grade added successfully for student {student.name}",
        "evaluation": avaliacao.to_dict()
    }


def update_grade(
    db: Session,
    teacher_id: int,
    grade_id: int,
    valor: Optional[float] = None,
    modulo: Optional[str] = None,
    descricao: Optional[str] = None,
    date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Update an existing grade.
    
    AUTHORIZATION: Teacher only.
    
    Args:
        db: Database session
        teacher_id: ID of the teacher updating the grade
        grade_id: ID of the evaluation to update
        valor: New grade value (optional)
        modulo: New module (optional)
        descricao: New description (optional)
        date: New date (optional)
        
    Returns:
        Updated evaluation data
        
    Raises:
        TeacherOnlyError: If requester is not a teacher
        ValidationError: If validation fails
    """
    auth_service = AuthorizationService(db)
    
    # ENFORCEMENT: Only teachers can update grades
    auth_service.enforce_teacher_only(teacher_id, "update_grade")
    
    # Get existing evaluation
    avaliacao = db.query(Avaliacao).filter(Avaliacao.id == grade_id).first()
    if not avaliacao:
        raise ValidationError(f"Grade with id {grade_id} not found", "grade_id")
    
    # Update fields if provided
    if valor is not None:
        if valor < 0 or valor > 20:
            raise ValidationError("Grade value must be between 0 and 20", "valor")
        avaliacao.valor = valor
    
    if modulo is not None:
        avaliacao.modulo = modulo
    
    if descricao is not None:
        avaliacao.descricao = descricao
    
    if date is not None:
        avaliacao.date = date
    
    # Update audit fields
    avaliacao.updated_by = teacher_id
    
    db.commit()
    db.refresh(avaliacao)
    
    return {
        "success": True,
        "message": "Grade updated successfully",
        "evaluation": avaliacao.to_dict()
    }


def delete_grade(*args, **kwargs):
    """
    DELETE IS NOT ALLOWED.
    This function exists to explicitly block delete attempts.
    
    Raises:
        FeatureNotAvailableError: Always
    """
    raise FeatureNotAvailableError(
        "delete_grade - Deleting grades is not allowed. "
        "Use update_grade to modify existing grades instead."
    )
