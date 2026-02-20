"""
Grade reading tools for the School Grades system.
Implements read operations with proper authorization enforcement.

CRITICAL RULE: Students can only see their own grades.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import Avaliacao, User, Disciplina, Turma, AlunoTurma
from .authorization import AuthorizationService
from .exceptions import ValidationError


def get_grades_by_student(
    db: Session,
    requester_id: int,
    student_id: int,
    disciplina_id: Optional[int] = None,
    modulo: Optional[str] = None,
    turma_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get grades for a specific student with optional filters.
    
    AUTHORIZATION:
    - Teachers: Can access any student's grades
    - Students: Can ONLY access their own grades
    
    Args:
        db: Database session
        requester_id: ID of the user making the request
        student_id: ID of the student whose grades to retrieve
        disciplina_id: Filter by subject (optional)
        modulo: Filter by module (optional)
        turma_id: Filter by class (optional)
        
    Returns:
        Dictionary with student info and grades
        
    Raises:
        StudentAccessDenied: If student tries to access another student's grades
    """
    auth_service = AuthorizationService(db)
    
    # CRITICAL ENFORCEMENT: Students can only access their own data
    auth_service.enforce_student_data_access(requester_id, student_id)
    
    # Get student info
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise ValidationError(f"Student with id {student_id} not found", "student_id")
    
    # Build query
    query = (
        db.query(Avaliacao)
        .filter(Avaliacao.user_id == student_id)
    )
    
    if disciplina_id:
        query = query.filter(Avaliacao.disciplina_id == disciplina_id)
    
    if modulo:
        query = query.filter(Avaliacao.modulo == modulo)
    
    if turma_id:
        query = query.filter(Avaliacao.turma_id == turma_id)
    
    # Order by date
    query = query.order_by(Avaliacao.date.desc())
    
    grades = query.all()
    
    return {
        "student": {
            "id": student.id,
            "name": student.name
        },
        "filters_applied": {
            "disciplina_id": disciplina_id,
            "modulo": modulo,
            "turma_id": turma_id
        },
        "total_grades": len(grades),
        "grades": [g.to_dict() for g in grades]
    }


def get_grades_by_disciplina(
    db: Session,
    requester_id: int,
    disciplina_id: int,
    turma_id: Optional[int] = None,
    modulo: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get grades for a specific disciplina.
    
    AUTHORIZATION:
    - Teachers: Can see all grades
    - Students: Can only see their own grades within the disciplina
    
    Args:
        db: Database session
        requester_id: ID of the user making the request
        disciplina_id: ID of the subject
        turma_id: Filter by class (optional)
        modulo: Filter by module (optional)
        
    Returns:
        Dictionary with disciplina info and grades
    """
    auth_service = AuthorizationService(db)
    role = auth_service.get_user_role(requester_id)
    
    # Get disciplina info
    disciplina = db.query(Disciplina).filter(Disciplina.id == disciplina_id).first()
    if not disciplina:
        raise ValidationError(f"Disciplina with id {disciplina_id} not found", "disciplina_id")
    
    # Build base query
    query = db.query(Avaliacao).filter(Avaliacao.disciplina_id == disciplina_id)
    
    # ENFORCEMENT: Students can only see their own grades
    if role == "student":
        query = query.filter(Avaliacao.user_id == requester_id)
    
    if turma_id:
        query = query.filter(Avaliacao.turma_id == turma_id)
    
    if modulo:
        query = query.filter(Avaliacao.modulo == modulo)
    
    query = query.order_by(Avaliacao.date.desc())
    
    grades = query.all()
    
    return {
        "disciplina": {
            "id": disciplina.id,
            "name": disciplina.name
        },
        "filters_applied": {
            "turma_id": turma_id,
            "modulo": modulo
        },
        "requester_role": role,
        "total_grades": len(grades),
        "grades": [g.to_dict() for g in grades]
    }


def get_grade_summary(
    db: Session,
    requester_id: int,
    student_id: int,
    disciplina_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get grade summary with averages for a student.
    
    AUTHORIZATION:
    - Teachers: Can access any student's summary
    - Students: Can ONLY access their own summary
    
    Args:
        db: Database session
        requester_id: ID of the user making the request
        student_id: ID of the student
        disciplina_id: Filter by subject (optional)
        
    Returns:
        Dictionary with summary, averages, and recent evaluations
    """
    auth_service = AuthorizationService(db)
    
    # CRITICAL ENFORCEMENT: Students can only access their own data
    auth_service.enforce_student_data_access(requester_id, student_id)
    
    # Get student info
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise ValidationError(f"Student with id {student_id} not found", "student_id")
    
    # Build base query
    base_query = db.query(Avaliacao).filter(Avaliacao.user_id == student_id)
    
    if disciplina_id:
        base_query = base_query.filter(Avaliacao.disciplina_id == disciplina_id)
    
    # Get all grades
    grades = base_query.all()
    
    if not grades:
        return {
            "student": {"id": student.id, "name": student.name},
            "disciplina_id": disciplina_id,
            "total_evaluations": 0,
            "average": None,
            "min_grade": None,
            "max_grade": None,
            "recent_evaluations": []
        }
    
    # Calculate statistics
    valores = [g.valor for g in grades]
    average = sum(valores) / len(valores)
    
    # Get recent evaluations
    recent = sorted(grades, key=lambda x: x.date, reverse=True)[:5]
    
    # Get averages by disciplina (if no filter applied)
    averages_by_disciplina = {}
    if not disciplina_id:
        disciplinas_query = (
            db.query(
                Disciplina.id,
                Disciplina.name,
                func.avg(Avaliacao.valor).label("average"),
                func.count(Avaliacao.id).label("count")
            )
            .join(Avaliacao, Avaliacao.disciplina_id == Disciplina.id)
            .filter(Avaliacao.user_id == student_id)
            .group_by(Disciplina.id)
            .all()
        )
        for d_id, d_name, d_avg, d_count in disciplinas_query:
            averages_by_disciplina[d_name] = {
                "id": d_id,
                "average": round(float(d_avg), 2),
                "total_evaluations": d_count
            }
    
    return {
        "student": {"id": student.id, "name": student.name},
        "disciplina_id": disciplina_id,
        "total_evaluations": len(grades),
        "average": round(average, 2),
        "min_grade": min(valores),
        "max_grade": max(valores),
        "averages_by_disciplina": averages_by_disciplina if not disciplina_id else None,
        "recent_evaluations": [g.to_dict() for g in recent]
    }


def get_my_grades(
    db: Session,
    user_id: int,
    disciplina_id: Optional[int] = None,
    modulo: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function for students to get their own grades.
    Always uses the requester's ID as the student ID.
    
    Args:
        db: Database session
        user_id: ID of the requesting student
        disciplina_id: Filter by subject (optional)
        modulo: Filter by module (optional)
        
    Returns:
        Dictionary with grades
    """
    # This is safe because we're using user_id for both requester and target
    return get_grades_by_student(
        db=db,
        requester_id=user_id,
        student_id=user_id,  # Always own grades
        disciplina_id=disciplina_id,
        modulo=modulo
    )


def get_my_summary(
    db: Session,
    user_id: int,
    disciplina_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Convenience function for students to get their own summary.
    Always uses the requester's ID as the student ID.
    
    Args:
        db: Database session
        user_id: ID of the requesting student
        disciplina_id: Filter by subject (optional)
        
    Returns:
        Dictionary with summary
    """
    return get_grade_summary(
        db=db,
        requester_id=user_id,
        student_id=user_id,  # Always own summary
        disciplina_id=disciplina_id
    )
