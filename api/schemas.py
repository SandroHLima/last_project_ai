from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field


# Request schemas
class AgentRequest(BaseModel):
    user_id: int = Field(..., description="ID of the requesting user")
    message: str = Field(..., description="User's message/query", min_length=1)
    show_all: Optional[bool] = Field(False, description="Whether to request full results (no truncation)")


class AddGradeRequest(BaseModel):
    teacher_id: int = Field(..., description="ID of the teacher adding the grade")
    student_id: int = Field(..., description="ID of the student")
    disciplina_id: int = Field(..., description="ID of the subject")
    turma_id: int = Field(..., description="ID of the class")
    modulo: str = Field(..., description="Module identifier")
    descricao: str = Field(..., description="Evaluation description")
    valor: float = Field(..., ge=0, le=20, description="Grade value (0-20)")
    date: Optional[datetime] = Field(None, description="Evaluation date")


class UpdateGradeRequest(BaseModel):
    teacher_id: int = Field(..., description="ID of the teacher")
    grade_id: int = Field(..., description="ID of the grade to update")
    valor: Optional[float] = Field(None, ge=0, le=20, description="New grade value")
    modulo: Optional[str] = Field(None, description="New module")
    descricao: Optional[str] = Field(None, description="New description")


class GradesQueryRequest(BaseModel):
    requester_id: int = Field(..., description="ID of the requesting user")
    student_id: Optional[int] = Field(None, description="Filter by student ID")
    disciplina_id: Optional[int] = Field(None, description="Filter by subject ID")
    turma_id: Optional[int] = Field(None, description="Filter by class ID")
    modulo: Optional[str] = Field(None, description="Filter by module")


class ClassReportRequest(BaseModel):
    requester_id: int = Field(..., description="ID of the requesting teacher")
    turma_id: int = Field(..., description="Class ID")
    disciplina_id: Optional[int] = Field(None, description="Filter by subject")
    modulo: Optional[str] = Field(None, description="Filter by module")


class CreateUserRequest(BaseModel):
    name: str = Field(..., description="Full name of the user", min_length=1)
    role: str = Field(..., description="Role: 'student' or 'teacher'")
    turma_ids: Optional[List[int]] = Field(None, description="Optional list of turma IDs to assign (students only)")


# Response schemas
class AgentResponse(BaseModel):
    response: str = Field(..., description="Agent's response text")
    blocked: bool = Field(default=False, description="Whether request was blocked")
    intent: str = Field(..., description="Detected intent")
    tool_result: Optional[Any] = Field(None, description="Raw tool result")
    error: Optional[str] = Field(None, description="Error message if any")


class UserResponse(BaseModel):
    id: int
    name: str
    role: str


class TurmaResponse(BaseModel):
    id: int
    name: str


class GradeResponse(BaseModel):
    id: int
    user_id: int
    student_name: Optional[str]
    disciplina_id: int
    disciplina_name: Optional[str]
    turma_id: int
    turma_name: Optional[str]
    modulo: str
    descricao: str
    valor: float
    date: Optional[str]
    updated_by: Optional[int]
    updated_at: Optional[str]


class GradesListResponse(BaseModel):
    student: Optional[dict]
    filters_applied: dict
    total_grades: int
    grades: List[dict]


class SummaryResponse(BaseModel):
    student: dict
    disciplina_id: Optional[int]
    total_evaluations: int
    average: Optional[float]
    min_grade: Optional[float]
    max_grade: Optional[float]
    averages_by_disciplina: Optional[dict]
    recent_evaluations: List[dict]


class ClassReportResponse(BaseModel):
    turma: dict
    filters_applied: dict
    total_students: int
    class_statistics: Optional[dict]
    students: List[dict]


class ErrorResponse(BaseModel):
    detail: str
    error_type: Optional[str]


class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any]
