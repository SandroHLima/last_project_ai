"""
Authorization module for the School Grades system.
Implements role-based access control with enforcement at the tool layer.

CRITICAL RULES:
1. Never trust the client for role - always get from DB
2. Students can only access their own data  
3. Teachers can access all data and modify grades
4. No DELETE operations exist
"""
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
    """
    Service for handling authorization checks.
    All role information is fetched from the database, never trusted from client.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user(self, user_id: int) -> User:
        """
        Get user from database.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            User object with id, name, and role
            
        Raises:
            InvalidUserError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise InvalidUserError(user_id)
        return user
    
    def get_user_role(self, user_id: int) -> str:
        """
        Get user's role from database.
        NEVER trust client-provided role.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            Role string ('student' or 'teacher')
        """
        user = self.get_user(user_id)
        return user.role
    
    def is_teacher(self, user_id: int) -> bool:
        """Check if user is a teacher."""
        return self.get_user_role(user_id) == "teacher"
    
    def is_student(self, user_id: int) -> bool:
        """Check if user is a student."""
        return self.get_user_role(user_id) == "student"
    
    def enforce_teacher_only(self, user_id: int, action: str) -> None:
        """
        Enforce that only teachers can perform an action.
        
        Args:
            user_id: The requesting user's ID
            action: Description of the action being attempted
            
        Raises:
            TeacherOnlyError: If user is not a teacher
        """
        if not self.is_teacher(user_id):
            raise TeacherOnlyError(user_id, action)
    
    def enforce_student_data_access(
        self, 
        requester_id: int, 
        target_student_id: int
    ) -> None:
        """
        Enforce that students can only access their own data.
        Teachers can access any student's data.
        
        This is the CRITICAL enforcement layer that prevents
        students from accessing other students' data.
        
        Args:
            requester_id: The ID of the user making the request
            target_student_id: The ID of the student whose data is being accessed
            
        Raises:
            StudentAccessDenied: If a student tries to access another student's data
        """
        role = self.get_user_role(requester_id)
        
        # Teachers can access any student's data
        if role == "teacher":
            return
        
        # Students can only access their own data
        if role == "student" and requester_id != target_student_id:
            raise StudentAccessDenied(requester_id, target_student_id)
    
    def can_modify_grades(self, user_id: int) -> bool:
        """
        Check if user can add/update grades.
        Only teachers can modify grades.
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if user can modify grades, False otherwise
        """
        return self.is_teacher(user_id)
    
    def can_view_class_report(self, user_id: int) -> bool:
        """
        Check if user can view class reports.
        Only teachers can view class reports (contains all students' data).
        
        Args:
            user_id: The user ID to check
            
        Returns:
            True if user can view class reports, False otherwise
        """
        return self.is_teacher(user_id)


def get_authorization_service(db: Session) -> AuthorizationService:
    """Factory function to create AuthorizationService."""
    return AuthorizationService(db)
