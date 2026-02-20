"""
Tools module for the School Grades system.

This module provides all the tools needed for the agent to interact
with the database while enforcing authorization rules.
"""
from .exceptions import (
    AuthorizationError,
    StudentAccessDenied,
    TeacherOnlyError,
    InvalidUserError,
    ValidationError,
    FeatureNotAvailableError,
)

from .authorization import (
    AuthorizationService,
    get_authorization_service,
)

from .identity import (
    get_user,
    get_user_with_classes,
    get_students_in_class,
    find_student_by_name,
    list_users,
    list_turmas,
    create_user,
)

from .grades_write import (
    add_grade,
    update_grade,
    delete_grade,  # Always raises FeatureNotAvailableError
)

from .grades_read import (
    get_grades_by_student,
    get_grades_by_disciplina,
    get_grade_summary,
    get_my_grades,
    get_my_summary,
)

from .reporting import (
    get_class_report,
    compute_statistics,
    get_disciplina_report,
    get_module_report,
)

__all__ = [
    # Exceptions
    "AuthorizationError",
    "StudentAccessDenied",
    "TeacherOnlyError",
    "InvalidUserError",
    "ValidationError",
    "FeatureNotAvailableError",
    # Authorization
    "AuthorizationService",
    "get_authorization_service",
    # Identity
    "get_user",
    "get_user_with_classes",
    "get_students_in_class",
    "find_student_by_name",
    "list_users",
    "create_user",
    "list_turmas",
    # Grades Write
    "add_grade",
    "update_grade",
    "delete_grade",
    # Grades Read
    "get_grades_by_student",
    "get_grades_by_disciplina",
    "get_grade_summary",
    "get_my_grades",
    "get_my_summary",
    # Reporting
    "get_class_report",
    "compute_statistics",
    "get_disciplina_report",
    "get_module_report",
]
