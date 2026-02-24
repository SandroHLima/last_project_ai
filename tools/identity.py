from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from database import User, AlunoTurma, Turma
from .authorization import AuthorizationService


def get_user(db: Session, user_id: int) -> Dict[str, Any]:
    auth_service = AuthorizationService(db)
    user = auth_service.get_user(user_id)
    
    return {
        "id": user.id,
        "name": user.name,
        "role": user.role
    }


def get_user_with_classes(db: Session, user_id: int) -> Dict[str, Any]:
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


def list_users(db: Session, role: Optional[str] = None) -> list[Dict[str, Any]]:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    users = query.all()
    return [{"id": u.id, "name": u.name, "role": u.role} for u in users]


def list_turmas(db: Session) -> list[Dict[str, Any]]:
    turmas = db.query(Turma).all()
    return [{"id": t.id, "name": t.name} for t in turmas]


def create_user(db: Session, name: str, role: str, turma_ids: Optional[list[int]] = None) -> Dict[str, Any]:
    from .exceptions import ValidationError
    # Basic validation
    if role not in ("student", "teacher"):
        raise ValidationError("Invalid role. Must be 'student' or 'teacher'", field="role")

    user = User(name=name, role=role)
    db.add(user)
    db.flush()

    # If student and turma_ids provided, create associations
    if role == "student" and turma_ids:
        for t_id in turma_ids:
            turma = db.query(Turma).filter(Turma.id == t_id).first()
            if not turma:
                raise ValidationError(f"Turma id {t_id} not found", field="turma_id")
            assoc = AlunoTurma(user_id=user.id, turma_id=t_id)
            db.add(assoc)

    db.commit()
    return {"id": user.id, "name": user.name, "role": user.role}
