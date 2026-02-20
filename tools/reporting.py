"""
Reporting tools for the School Grades system.
All reporting functions are restricted to teachers only.
"""
from typing import Dict, Any, Optional, List
from statistics import mean, median
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import Avaliacao, User, Disciplina, Turma, AlunoTurma
from .authorization import AuthorizationService
from .exceptions import ValidationError


def get_class_report(
    db: Session,
    requester_id: int,
    turma_id: int,
    disciplina_id: Optional[int] = None,
    modulo: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a comprehensive report for a class.
    
    AUTHORIZATION: Teacher only.
    
    Args:
        db: Database session
        requester_id: ID of the requesting teacher
        turma_id: ID of the class
        disciplina_id: Filter by subject (optional)
        modulo: Filter by module (optional)
        
    Returns:
        Dictionary with class report including all students and their averages
        
    Raises:
        TeacherOnlyError: If requester is not a teacher
    """
    auth_service = AuthorizationService(db)
    
    # ENFORCEMENT: Only teachers can view class reports
    auth_service.enforce_teacher_only(requester_id, "view_class_report")
    
    # Get turma info
    turma = db.query(Turma).filter(Turma.id == turma_id).first()
    if not turma:
        raise ValidationError(f"Turma with id {turma_id} not found", "turma_id")
    
    # Get all students in the class
    students_in_class = (
        db.query(User)
        .join(AlunoTurma, User.id == AlunoTurma.user_id)
        .filter(AlunoTurma.turma_id == turma_id)
        .filter(User.role == "student")
        .all()
    )
    
    # Build student reports
    student_reports = []
    all_grades = []
    
    for student in students_in_class:
        # Get grades for this student
        query = (
            db.query(Avaliacao)
            .filter(Avaliacao.user_id == student.id)
            .filter(Avaliacao.turma_id == turma_id)
        )
        
        if disciplina_id:
            query = query.filter(Avaliacao.disciplina_id == disciplina_id)
        
        if modulo:
            query = query.filter(Avaliacao.modulo == modulo)
        
        grades = query.all()
        valores = [g.valor for g in grades]
        all_grades.extend(valores)
        
        student_report = {
            "student_id": student.id,
            "student_name": student.name,
            "total_evaluations": len(grades),
            "average": round(mean(valores), 2) if valores else None,
            "min_grade": min(valores) if valores else None,
            "max_grade": max(valores) if valores else None,
            "grades": [g.to_dict() for g in grades]
        }
        student_reports.append(student_report)
    
    # Calculate class statistics
    class_stats = compute_statistics(all_grades) if all_grades else None
    
    return {
        "turma": {
            "id": turma.id,
            "name": turma.name
        },
        "filters_applied": {
            "disciplina_id": disciplina_id,
            "modulo": modulo
        },
        "total_students": len(students_in_class),
        "class_statistics": class_stats,
        "students": student_reports
    }


def compute_statistics(grades: List[float]) -> Dict[str, Any]:
    """
    Compute statistics for a list of grades.
    
    Args:
        grades: List of grade values
        
    Returns:
        Dictionary with mean, median, min, max, total
    """
    if not grades:
        return {
            "mean": None,
            "median": None,
            "min": None,
            "max": None,
            "total_grades": 0
        }
    
    return {
        "mean": round(mean(grades), 2),
        "median": round(median(grades), 2),
        "min": min(grades),
        "max": max(grades),
        "total_grades": len(grades)
    }


def get_disciplina_report(
    db: Session,
    requester_id: int,
    disciplina_id: int,
    turma_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get a report for a specific disciplina.
    
    AUTHORIZATION: Teacher only.
    
    Args:
        db: Database session
        requester_id: ID of the requesting teacher
        disciplina_id: ID of the subject
        turma_id: Filter by class (optional)
        
    Returns:
        Dictionary with disciplina report
    """
    auth_service = AuthorizationService(db)
    auth_service.enforce_teacher_only(requester_id, "view_disciplina_report")
    
    # Get disciplina info
    disciplina = db.query(Disciplina).filter(Disciplina.id == disciplina_id).first()
    if not disciplina:
        raise ValidationError(f"Disciplina with id {disciplina_id} not found", "disciplina_id")
    
    # Build query
    query = (
        db.query(
            User.id,
            User.name,
            func.avg(Avaliacao.valor).label("average"),
            func.min(Avaliacao.valor).label("min_grade"),
            func.max(Avaliacao.valor).label("max_grade"),
            func.count(Avaliacao.id).label("total_evaluations")
        )
        .join(Avaliacao, User.id == Avaliacao.user_id)
        .filter(Avaliacao.disciplina_id == disciplina_id)
    )
    
    if turma_id:
        query = query.filter(Avaliacao.turma_id == turma_id)
    
    query = query.group_by(User.id).order_by(User.name)
    
    results = query.all()
    
    # Build student summaries
    student_summaries = [
        {
            "student_id": r.id,
            "student_name": r.name,
            "average": round(float(r.average), 2) if r.average else None,
            "min_grade": float(r.min_grade) if r.min_grade else None,
            "max_grade": float(r.max_grade) if r.max_grade else None,
            "total_evaluations": r.total_evaluations
        }
        for r in results
    ]
    
    # Compute overall statistics
    all_averages = [s["average"] for s in student_summaries if s["average"] is not None]
    
    return {
        "disciplina": {
            "id": disciplina.id,
            "name": disciplina.name
        },
        "turma_id": turma_id,
        "total_students": len(student_summaries),
        "class_average": round(mean(all_averages), 2) if all_averages else None,
        "students": student_summaries
    }


def get_module_report(
    db: Session,
    requester_id: int,
    modulo: str,
    disciplina_id: Optional[int] = None,
    turma_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get a report for a specific module.
    
    AUTHORIZATION: Teacher only.
    
    Args:
        db: Database session
        requester_id: ID of the requesting teacher
        modulo: Module name
        disciplina_id: Filter by subject (optional)
        turma_id: Filter by class (optional)
        
    Returns:
        Dictionary with module report
    """
    auth_service = AuthorizationService(db)
    auth_service.enforce_teacher_only(requester_id, "view_module_report")
    
    # Build query
    query = (
        db.query(
            User.id,
            User.name,
            Disciplina.name.label("disciplina_name"),
            func.avg(Avaliacao.valor).label("average"),
            func.count(Avaliacao.id).label("total_evaluations")
        )
        .join(Avaliacao, User.id == Avaliacao.user_id)
        .join(Disciplina, Avaliacao.disciplina_id == Disciplina.id)
        .filter(Avaliacao.modulo == modulo)
    )
    
    if disciplina_id:
        query = query.filter(Avaliacao.disciplina_id == disciplina_id)
    
    if turma_id:
        query = query.filter(Avaliacao.turma_id == turma_id)
    
    query = query.group_by(User.id, Disciplina.name).order_by(User.name)
    
    results = query.all()
    
    # Build summaries
    summaries = [
        {
            "student_id": r.id,
            "student_name": r.name,
            "disciplina": r.disciplina_name,
            "average": round(float(r.average), 2) if r.average else None,
            "total_evaluations": r.total_evaluations
        }
        for r in results
    ]
    
    return {
        "modulo": modulo,
        "filters_applied": {
            "disciplina_id": disciplina_id,
            "turma_id": turma_id
        },
        "total_records": len(summaries),
        "results": summaries
    }
