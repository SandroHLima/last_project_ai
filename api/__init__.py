"""API module for the School Grades system."""
from .routes import agent_router, tools_router, users_router
from .schemas import (
    AgentRequest,
    AgentResponse,
    AddGradeRequest,
    UpdateGradeRequest,
    GradesQueryRequest,
    ClassReportRequest,
    UserResponse,
    GradesListResponse,
    SummaryResponse,
    ClassReportResponse,
    SuccessResponse,
    ErrorResponse,
)

__all__ = [
    "agent_router",
    "tools_router", 
    "users_router",
    "AgentRequest",
    "AgentResponse",
    "AddGradeRequest",
    "UpdateGradeRequest",
    "GradesQueryRequest",
    "ClassReportRequest",
    "UserResponse",
    "GradesListResponse",
    "SummaryResponse",
    "ClassReportResponse",
    "SuccessResponse",
    "ErrorResponse",
]
