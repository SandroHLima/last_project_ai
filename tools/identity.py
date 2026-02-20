"""
Identity tools for the School Grades system.
Handles user identification and role retrieval.
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from database import User, AlunoTurma, Turma
from .authorization import AuthorizationService


def get_user(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get user information from database.
    
    Args:
        db: Database session
        user_id: The user ID to look up
        
    Returns:
        Dictionary with user id, name, and role
        
    Raises:
        InvalidUserError: If user not found
    """
    auth_service = AuthorizationService(db)
    user = auth_service.get_user(user_id)
    
    return {
        "id": user.id,
        "name": user.name,
        "role": user.role
    }


def get_user_with_classes(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get user information with their classes.
    
    Args:
        db: Database session
        user_id: The user ID to look up
        
    Returns:
        Dictionary with user info and their classes (for students)
    """
    user_info = get_user(db, user_id)
    
    # Get classes if student
    if user_info["role"] == "student":
        aluno_turmas = (
            db.query(AlunoTurma, Turma)
            .join(Turma, AlunoTurma.turma_id == Turma.id)
            .filter(AlunoTurma.user_id == user_id)
            .all()
        )
        user_info["turmas"] = [
            {"id": turma.id, "name": turma.name}
            for _, turma in aluno_turmas
        ]
    
    return user_info


def get_students_in_class(
    db: Session, 
    requester_id: int, 
    turma_id: int
) -> list[Dict[str, Any]]:
    """
    Get all students in a class (teacher only).
    
    Args:
        db: Database session
        requester_id: The requesting user's ID
        turma_id: The class ID
        
    Returns:
        List of students in the class
        
    Raises:
        TeacherOnlyError: If requester is not a teacher
    """
    auth_service = AuthorizationService(db)
    auth_service.enforce_teacher_only(requester_id, "view_students_in_class")
    
    students = (
        db.query(User)
        .join(AlunoTurma, User.id == AlunoTurma.user_id)
        .filter(AlunoTurma.turma_id == turma_id)
        .filter(User.role == "student")
        .all()
    )
    
    return [
        {"id": s.id, "name": s.name, "role": s.role}
        for s in students
    ]


def find_student_by_name(
    db: Session,
    requester_id: int,
    name: str
) -> Optional[Dict[str, Any]]:
    """
    Find a student by name (partial match).
    Teachers only - students cannot search for other students.
    
    Args:
        db: Database session
        requester_id: The requesting user's ID
        name: Name to search for
        
    Returns:
        Student info if found, None otherwise
        
    Raises:
        TeacherOnlyError: If requester is not a teacher
    """
    auth_service = AuthorizationService(db)
    auth_service.enforce_teacher_only(requester_id, "search_students")
    
    student = (
        db.query(User)
        .filter(User.role == "student")
        .filter(User.name.ilike(f"%{name}%"))
        .first()
    )
    
    if student:
        return {
            "id": student.id,
            "name": student.name,
            "role": student.role
        }
    return None
