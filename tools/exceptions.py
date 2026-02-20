"""
Custom exceptions for the School Grades system.
"""


class AuthorizationError(Exception):
    """Raised when a user attempts an unauthorized action."""
    
    def __init__(self, message: str, user_id: int = None, action: str = None):
        self.message = message
        self.user_id = user_id
        self.action = action
        super().__init__(self.message)


class StudentAccessDenied(AuthorizationError):
    """Raised when a student tries to access another student's data."""
    
    def __init__(self, requester_id: int, target_id: int):
        message = f"Access denied: Student {requester_id} cannot access data of student {target_id}"
        super().__init__(message, user_id=requester_id, action="access_other_student")


class TeacherOnlyError(AuthorizationError):
    """Raised when a non-teacher tries to perform a teacher-only action."""
    
    def __init__(self, user_id: int, action: str):
        message = f"Access denied: Only teachers can perform '{action}'"
        super().__init__(message, user_id=user_id, action=action)


class InvalidUserError(Exception):
    """Raised when a user is not found."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User with id {user_id} not found")


class ValidationError(Exception):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class FeatureNotAvailableError(Exception):
    """Raised when attempting to use a feature that doesn't exist."""
    
    def __init__(self, feature: str):
        self.feature = feature
        super().__init__(f"Feature not available: {feature}")
