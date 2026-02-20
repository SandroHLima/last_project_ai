"""
Agent state definition for the School Grades LangGraph agent.
"""
from typing import TypedDict, Optional, Any, List
from enum import Enum


class Intent(str, Enum):
    """Possible intents detected from user messages."""
    ADD_GRADE = "add_grade"
    UPDATE_GRADE = "update_grade"
    QUERY_GRADES = "query_grades"
    SUMMARY = "summary"
    CLASS_REPORT = "class_report"
    FALLBACK = "fallback"
    BLOCKED = "blocked"  # Used when guardrail blocks the request


class AgentState(TypedDict, total=False):
    """
    State maintained throughout the agent workflow.
    
    Attributes:
        user_id: The ID of the requesting user
        role: The user's role (from database, never from client)
        message: The original user message
        intent: Detected intent
        entities: Extracted entities from the message
        missing_fields: Fields that are required but not provided
        tool_result: Result from tool execution
        error: Error message if something failed
        response: Final response to return to user
        blocked: Whether the request was blocked by guardrail
        blocked_reason: Reason for blocking
    """
    # User context (loaded from DB)
    user_id: int
    role: str
    user_name: str
    
    # Input
    message: str
    
    # Intent and entities
    intent: Intent
    entities: dict
    
    # Missing fields handling
    missing_fields: List[str]
    ask_missing_fields: bool
    
    # Execution results
    tool_result: Any
    error: Optional[str]
    
    # Response
    response: str
    
    # Guardrail
    blocked: bool
    blocked_reason: Optional[str]


class Entities(TypedDict, total=False):
    """
    Entities extracted from user message.
    
    Used for:
    - ADD_GRADE: student_id, disciplina_id, turma_id, modulo, descricao, valor
    - UPDATE_GRADE: grade_id, valor, modulo, descricao
    - QUERY_GRADES: student_id, disciplina_id, modulo, turma_id
    - SUMMARY: student_id, disciplina_id
    - CLASS_REPORT: turma_id, disciplina_id, modulo
    """
    # Student identification
    student_id: Optional[int]
    student_name: Optional[str]  # For name-based lookup
    
    # Grade data
    grade_id: Optional[int]
    valor: Optional[float]
    
    # Context
    disciplina_id: Optional[int]
    disciplina_name: Optional[str]
    turma_id: Optional[int]
    turma_name: Optional[str]
    modulo: Optional[str]
    descricao: Optional[str]
    
    # Date (optional)
    date: Optional[str]


# Required fields for each intent
REQUIRED_FIELDS = {
    Intent.ADD_GRADE: ["student_id", "disciplina_id", "turma_id", "modulo", "descricao", "valor"],
    Intent.UPDATE_GRADE: ["grade_id"],  # At least one of: valor, modulo, descricao
    Intent.QUERY_GRADES: [],  # student_id defaults to self for students
    Intent.SUMMARY: [],  # student_id defaults to self for students
    Intent.CLASS_REPORT: ["turma_id"],
    Intent.FALLBACK: [],
    Intent.BLOCKED: [],
}
