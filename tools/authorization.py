from typing import Optional
from sqlalchemy.orm import Session

from database import User
from .exceptions import (
    AuthorizationError, 
    StudentAccessDenied, 
    TeacherOnlyError,
    InvalidUserError
)


class AuthorizationService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user(self, user_id: int) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise InvalidUserError(user_id)
        return user
    
    def get_user_role(self, user_id: int) -> str:
        user = self.get_user(user_id)
        return user.role
    
    def is_teacher(self, user_id: int) -> bool:
        return self.get_user_role(user_id) == "teacher"
    
    def is_student(self, user_id: int) -> bool:
        return self.get_user_role(user_id) == "student"
    
    def enforce_teacher_only(self, user_id: int, action: str) -> None:
        if not self.is_teacher(user_id):
            raise TeacherOnlyError(user_id, action)
    
    def enforce_student_data_access(
        self, 
        requester_id: int, 
        target_student_id: int
    ) -> None:
        role = self.get_user_role(requester_id)
        
        if role == "teacher":
            return
        
        if role == "student" and requester_id != target_student_id:
            raise StudentAccessDenied(requester_id, target_student_id)
    
    def can_modify_grades(self, user_id: int) -> bool:
        return self.is_teacher(user_id)
    
    def can_view_class_report(self, user_id: int) -> bool:
        return self.is_teacher(user_id)


def get_authorization_service(db: Session) -> AuthorizationService:
    return AuthorizationService(db)
