"""
API routes for the School Grades system.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from tools import (
    get_user,
    get_user_with_classes,
    create_user,
    list_users,
    list_turmas,
    add_grade,
    update_grade,
    get_grades_by_student,
    get_grade_summary,
    get_class_report,
    get_grades_by_disciplina,
    StudentAccessDenied,
    TeacherOnlyError,
    ValidationError,
    InvalidUserError,
    FeatureNotAvailableError,
)
from agent import run_agent
from .schemas import (
    AgentRequest,
    AgentResponse,
    AddGradeRequest,
    UpdateGradeRequest,
    GradesQueryRequest,
    ClassReportRequest,
    CreateUserRequest,
    UserResponse,
    TurmaResponse,
    GradesListResponse,
    SummaryResponse,
    ClassReportResponse,
    SuccessResponse,
    ErrorResponse,
)


# Router for agent endpoints
agent_router = APIRouter(prefix="/agent", tags=["Agent"])

# Router for direct tool access
tools_router = APIRouter(prefix="/tools", tags=["Tools"])

# Router for user endpoints
users_router = APIRouter(prefix="/users", tags=["Users"])


# ============== Agent Endpoints ==============

@agent_router.post("/chat", response_model=AgentResponse)
async def agent_chat(request: AgentRequest, db: Session = Depends(get_db)):
    """
    Main agent endpoint - process natural language requests.
    
    This endpoint uses the LangGraph agent to:
    1. Load user context from database
    2. Check guardrails
    3. Parse intent and entities
    4. Execute appropriate tools
    5. Sanitize and return response
    """
    try:
        result = run_agent(
            user_id=request.user_id,
            message=request.message
        )
        return AgentResponse(**result)
    except InvalidUserError:
        raise HTTPException(status_code=404, detail="User not found")


@users_router.post("/", response_model=UserResponse)
async def create_user_endpoint(request: CreateUserRequest, db: Session = Depends(get_db)):
    """Create a new user (student or teacher)."""
    try:
        user = create_user(db=db, name=request.name, role=request.role, turma_ids=request.turma_ids)
        return UserResponse(**user)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@users_router.get("/", response_model=list[UserResponse])
async def get_users_endpoint(role: str | None = None, db: Session = Depends(get_db)):
    """List users. Optional query param `role` filters by 'student' or 'teacher'."""
    try:
        users = list_users(db=db, role=role)
        return [UserResponse(**u) for u in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@tools_router.get("/turmas", response_model=list[TurmaResponse])
async def get_turmas_endpoint(db: Session = Depends(get_db)):
    """Return list of turmas (classes)."""
    try:
        turmas = list_turmas(db=db)
        return [TurmaResponse(**t) for t in turmas]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== User Endpoints ==============

@users_router.get("/{user_id}", response_model=UserResponse)
async def get_user_info(user_id: int, db: Session = Depends(get_db)):
    """Get user information."""
    try:
        user = get_user(db, user_id)
        return UserResponse(**user)
    except InvalidUserError:
        raise HTTPException(status_code=404, detail="User not found")


@users_router.get("/{user_id}/details")
async def get_user_details(user_id: int, db: Session = Depends(get_db)):
    """Get user information with additional details (classes for students)."""
    try:
        return get_user_with_classes(db, user_id)
    except InvalidUserError:
        raise HTTPException(status_code=404, detail="User not found")


# ============== Tool Endpoints ==============

@tools_router.post("/grades/add", response_model=SuccessResponse)
async def add_grade_direct(request: AddGradeRequest, db: Session = Depends(get_db)):
    """
    Add a new grade (Teacher only).
    
    Direct tool access - bypasses natural language processing.
    """
    try:
        result = add_grade(
            db=db,
            teacher_id=request.teacher_id,
            student_id=request.student_id,
            disciplina_id=request.disciplina_id,
            turma_id=request.turma_id,
            modulo=request.modulo,
            descricao=request.descricao,
            valor=request.valor,
            date=request.date
        )
        return SuccessResponse(
            success=True,
            message=result.get("message", "Grade added"),
            data=result.get("evaluation")
        )
    except TeacherOnlyError:
        raise HTTPException(
            status_code=403, 
            detail="Only teachers can add grades"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InvalidUserError:
        raise HTTPException(status_code=404, detail="User not found")


@tools_router.post("/grades/update", response_model=SuccessResponse)
async def update_grade_direct(request: UpdateGradeRequest, db: Session = Depends(get_db)):
    """
    Update an existing grade (Teacher only).
    """
    try:
        result = update_grade(
            db=db,
            teacher_id=request.teacher_id,
            grade_id=request.grade_id,
            valor=request.valor,
            modulo=request.modulo,
            descricao=request.descricao
        )
        return SuccessResponse(
            success=True,
            message=result.get("message", "Grade updated"),
            data=result.get("evaluation")
        )
    except TeacherOnlyError:
        raise HTTPException(
            status_code=403,
            detail="Only teachers can update grades"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)


@tools_router.post("/grades/query", response_model=GradesListResponse)
async def query_grades(request: GradesQueryRequest, db: Session = Depends(get_db)):
    """
    Query grades with filters.
    
    Students can only query their own grades.
    Teachers can query any student's grades.
    """
    try:
        # If student_id not specified, default to requester's own grades
        student_id = request.student_id or request.requester_id
        
        result = get_grades_by_student(
            db=db,
            requester_id=request.requester_id,
            student_id=student_id,
            disciplina_id=request.disciplina_id,
            modulo=request.modulo,
            turma_id=request.turma_id
        )
        return GradesListResponse(**result)
    except StudentAccessDenied:
        raise HTTPException(
            status_code=403,
            detail="Cannot access other students' grades"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)


@tools_router.get("/grades/summary/{student_id}")
async def get_summary(
    student_id: int,
    requester_id: int,
    disciplina_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Get grade summary for a student.
    
    Students can only get their own summary.
    Teachers can get any student's summary.
    """
    try:
        return get_grade_summary(
            db=db,
            requester_id=requester_id,
            student_id=student_id,
            disciplina_id=disciplina_id
        )
    except StudentAccessDenied:
        raise HTTPException(
            status_code=403,
            detail="Cannot access other students' data"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)


@tools_router.post("/reports/class", response_model=ClassReportResponse)
async def get_class_report_endpoint(
    request: ClassReportRequest,
    db: Session = Depends(get_db)
):
    """
    Get class report (Teacher only).
    
    Returns all students in the class with their averages.
    """
    try:
        result = get_class_report(
            db=db,
            requester_id=request.requester_id,
            turma_id=request.turma_id,
            disciplina_id=request.disciplina_id,
            modulo=request.modulo
        )
        return ClassReportResponse(**result)
    except TeacherOnlyError:
        raise HTTPException(
            status_code=403,
            detail="Only teachers can view class reports"
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)


@tools_router.delete("/grades/{grade_id}")
async def delete_grade_endpoint(grade_id: int, teacher_id: int):
    """
    Delete a grade - NOT AVAILABLE.
    
    This endpoint always returns 405 as deletion is not allowed.
    """
    raise HTTPException(
        status_code=405,
        detail="Deleting grades is not allowed. Use update to modify grades."
    )
