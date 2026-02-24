from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import Avaliacao, User, Disciplina, Turma, AlunoTurma
from .authorization import AuthorizationService
from .exceptions import ValidationError, FeatureNotAvailableError


# ---------------------------------------------------------------------------
# WRITE operations (teacher-only)
# ---------------------------------------------------------------------------

def add_grade(
    db: Session,
    teacher_id: int,
    student_id: int,
    disciplina_id: int,
    turma_id: int,
    modulo: str,
    descricao: str,
    valor: float,
    date: Optional[datetime] = None,
) -> Dict[str, Any]:
    auth = AuthorizationService(db)
    auth.enforce_teacher_only(teacher_id, "add_grade")

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise ValidationError(f"Student with id {student_id} not found", "student_id")
    if student.role != "student":
        raise ValidationError(f"User {student_id} is not a student", "student_id")

    if not db.query(Disciplina).filter(Disciplina.id == disciplina_id).first():
        raise ValidationError(f"Disciplina with id {disciplina_id} not found", "disciplina_id")
    if not db.query(Turma).filter(Turma.id == turma_id).first():
        raise ValidationError(f"Turma with id {turma_id} not found", "turma_id")
    if valor < 0 or valor > 20:
        raise ValidationError("Grade value must be between 0 and 20", "valor")

    avaliacao = Avaliacao(
        user_id=student_id,
        disciplina_id=disciplina_id,
        turma_id=turma_id,
        modulo=modulo,
        descricao=descricao,
        valor=valor,
        date=date or datetime.now(),
        updated_by=teacher_id,
    )
    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)

    return {
        "success": True,
        "message": f"Grade added successfully for student {student.name}",
        "evaluation": avaliacao.to_dict(),
    }


def update_grade(
    db: Session,
    teacher_id: int,
    grade_id: int,
    valor: Optional[float] = None,
    modulo: Optional[str] = None,
    descricao: Optional[str] = None,
    date: Optional[datetime] = None,
) -> Dict[str, Any]:
    auth = AuthorizationService(db)
    auth.enforce_teacher_only(teacher_id, "update_grade")

    avaliacao = db.query(Avaliacao).filter(Avaliacao.id == grade_id).first()
    if not avaliacao:
        raise ValidationError(f"Grade with id {grade_id} not found", "grade_id")

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

    avaliacao.updated_by = teacher_id
    db.commit()
    db.refresh(avaliacao)

    return {
        "success": True,
        "message": "Grade updated successfully",
        "evaluation": avaliacao.to_dict(),
    }


def delete_grade(*args, **kwargs):
    raise FeatureNotAvailableError(
        "delete_grade - Deleting grades is not allowed. "
        "Use update_grade to modify existing grades instead."
    )


# ---------------------------------------------------------------------------
# READ operations
# ---------------------------------------------------------------------------

def get_grades_by_student(
    db: Session,
    requester_id: int,
    student_id: int,
    disciplina_id: Optional[int] = None,
    modulo: Optional[str] = None,
    turma_id: Optional[int] = None,
) -> Dict[str, Any]:
    auth = AuthorizationService(db)
    auth.enforce_student_data_access(requester_id, student_id)

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise ValidationError(f"Student with id {student_id} not found", "student_id")

    query = db.query(Avaliacao).filter(Avaliacao.user_id == student_id)
    if disciplina_id:
        query = query.filter(Avaliacao.disciplina_id == disciplina_id)
    if modulo:
        query = query.filter(Avaliacao.modulo == modulo)
    if turma_id:
        query = query.filter(Avaliacao.turma_id == turma_id)

    grades = query.order_by(Avaliacao.date.desc()).all()

    return {
        "student": {"id": student.id, "name": student.name},
        "filters_applied": {"disciplina_id": disciplina_id, "modulo": modulo, "turma_id": turma_id},
        "total_grades": len(grades),
        "grades": [g.to_dict() for g in grades],
    }


def get_grades_by_disciplina(
    db: Session,
    requester_id: int,
    disciplina_id: int,
    turma_id: Optional[int] = None,
    modulo: Optional[str] = None,
) -> Dict[str, Any]:
    auth = AuthorizationService(db)
    role = auth.get_user_role(requester_id)

    disciplina = db.query(Disciplina).filter(Disciplina.id == disciplina_id).first()
    if not disciplina:
        raise ValidationError(f"Disciplina with id {disciplina_id} not found", "disciplina_id")

    query = db.query(Avaliacao).filter(Avaliacao.disciplina_id == disciplina_id)
    if role == "student":
        query = query.filter(Avaliacao.user_id == requester_id)
    if turma_id:
        query = query.filter(Avaliacao.turma_id == turma_id)
    if modulo:
        query = query.filter(Avaliacao.modulo == modulo)

    grades = query.order_by(Avaliacao.date.desc()).all()

    return {
        "disciplina": {"id": disciplina.id, "name": disciplina.name},
        "filters_applied": {"turma_id": turma_id, "modulo": modulo},
        "requester_role": role,
        "total_grades": len(grades),
        "grades": [g.to_dict() for g in grades],
    }


def get_grade_summary(
    db: Session,
    requester_id: int,
    student_id: int,
    disciplina_id: Optional[int] = None,
) -> Dict[str, Any]:
    auth = AuthorizationService(db)
    auth.enforce_student_data_access(requester_id, student_id)

    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise ValidationError(f"Student with id {student_id} not found", "student_id")

    base = db.query(Avaliacao).filter(Avaliacao.user_id == student_id)
    if disciplina_id:
        base = base.filter(Avaliacao.disciplina_id == disciplina_id)

    grades = base.all()
    if not grades:
        return {
            "student": {"id": student.id, "name": student.name},
            "disciplina_id": disciplina_id,
            "total_evaluations": 0,
            "average": None, "min_grade": None, "max_grade": None,
            "recent_evaluations": [],
        }

    valores = [g.valor for g in grades]
    average = round(sum(valores) / len(valores), 2)
    recent = sorted(grades, key=lambda x: x.date, reverse=True)[:5]

    averages_by_disciplina = {}
    if not disciplina_id:
        rows = (
            db.query(Disciplina.id, Disciplina.name,
                     func.avg(Avaliacao.valor).label("average"),
                     func.count(Avaliacao.id).label("count"))
            .join(Avaliacao, Avaliacao.disciplina_id == Disciplina.id)
            .filter(Avaliacao.user_id == student_id)
            .group_by(Disciplina.id)
            .all()
        )
        for d_id, d_name, d_avg, d_count in rows:
            averages_by_disciplina[d_name] = {
                "id": d_id,
                "average": round(float(d_avg), 2),
                "total_evaluations": d_count,
            }

    return {
        "student": {"id": student.id, "name": student.name},
        "disciplina_id": disciplina_id,
        "total_evaluations": len(grades),
        "average": average,
        "min_grade": min(valores),
        "max_grade": max(valores),
        "averages_by_disciplina": averages_by_disciplina if not disciplina_id else None,
        "recent_evaluations": [g.to_dict() for g in recent],
    }


def get_my_grades(
    db: Session,
    user_id: int,
    disciplina_id: Optional[int] = None,
    modulo: Optional[str] = None,
) -> Dict[str, Any]:
    return get_grades_by_student(db=db, requester_id=user_id,
                                 student_id=user_id,
                                 disciplina_id=disciplina_id, modulo=modulo)


def get_my_summary(
    db: Session,
    user_id: int,
    disciplina_id: Optional[int] = None,
) -> Dict[str, Any]:
    return get_grade_summary(db=db, requester_id=user_id,
                             student_id=user_id,
                             disciplina_id=disciplina_id)
