"""
Guardrails module for the School Grades system.

Implements pre and post-processing guardrails to:
1. Block obvious unauthorized requests before they reach tools
2. Sanitize responses to prevent data leakage

DEFENSE IN DEPTH:
- Guardrails: Detect and block malicious intent
- Tool enforcement: Even if guardrails fail, tools enforce authorization
"""
import re
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

from tools.exceptions import AuthorizationError


class GuardrailResult(Enum):
    """Result of guardrail check."""
    ALLOW = "allow"
    BLOCK = "block"
    SANITIZE = "sanitize"


class GuardrailPre:
    """
    Pre-execution guardrail.
    Detects and blocks potentially malicious requests before tool execution.
    """
    
    # Patterns that indicate a student trying to access other students' data
    OTHER_STUDENT_PATTERNS = [
        r"notas?\s+(do|da|de)\s+(?!minhas?|meus?|minha)(\w+)",  # "notas do João"
        r"grades?\s+(of|for)\s+(?!my|mine)(\w+)",  # "grades of John"
        r"ver\s+notas?\s+(do|da|de)\s+(?!minhas?)(\w+)",  # "ver notas do Miguel"
        r"mostra\s+(as\s+)?notas?\s+(do|da|de)\s+(?!minhas?)(\w+)",  # "mostra as notas do Pedro"
        r"consultar?\s+notas?\s+(do|da|de)\s+(?!minhas?)(\w+)",  # "consultar notas da Ana"
        r"médias?\s+(do|da|de)\s+(?!minhas?)(\w+)",  # "média do João"
        r"relatório\s+(do|da|de)\s+aluno",  # "relatório do aluno"
        r"student_id\s*[:=]\s*(?!{user_id})\d+",  # explicit student_id different from user
    ]
    
    # Patterns that indicate deletion attempts
    DELETE_PATTERNS = [
        r"apagar\s+(nota|avaliação)",
        r"deletar?\s+(nota|avaliação)",
        r"remover\s+(nota|avaliação)",
        r"excluir\s+(nota|avaliação)",
        r"delete\s+(grade|evaluation)",
        r"remove\s+(grade|evaluation)",
    ]
    
    # Patterns that indicate write operations (for student blocking)
    WRITE_PATTERNS = [
        r"adicionar?\s+(nota|avaliação)",
        r"inserir\s+(nota|avaliação)",
        r"criar\s+(nota|avaliação)",
        r"atualizar\s+(nota|avaliação)",
        r"modificar\s+(nota|avaliação)",
        r"alterar\s+(nota|avaliação)",
        r"mudar\s+(nota|avaliação)",
        r"add\s+(grade|evaluation)",
        r"update\s+(grade|evaluation)",
        r"modify\s+(grade|evaluation)",
        r"change\s+(grade|evaluation)",
    ]
    
    def __init__(self, user_id: int, role: str):
        """
        Initialize guardrail with user context.
        
        Args:
            user_id: The requesting user's ID
            role: The user's role ('student' or 'teacher')
        """
        self.user_id = user_id
        self.role = role
    
    def check(self, message: str) -> Tuple[GuardrailResult, Optional[str]]:
        """
        Check if a request should be allowed.
        
        Args:
            message: The user's message/request
            
        Returns:
            Tuple of (result, reason if blocked)
        """
        message_lower = message.lower()
        
        # Check for deletion attempts (blocked for everyone)
        if self._matches_any_pattern(message_lower, self.DELETE_PATTERNS):
            return (
                GuardrailResult.BLOCK,
                "A eliminação de notas não é permitida no sistema. "
                "Se precisar corrigir uma nota, utilize a funcionalidade de atualização."
            )
        
        # Student-specific checks
        if self.role == "student":
            # Check for other student data access
            if self._matches_any_pattern(message_lower, self.OTHER_STUDENT_PATTERNS):
                return (
                    GuardrailResult.BLOCK,
                    "Não é possível aceder às notas de outros alunos. "
                    "Apenas pode consultar as suas próprias notas."
                )
            
            # Check for write operations
            if self._matches_any_pattern(message_lower, self.WRITE_PATTERNS):
                return (
                    GuardrailResult.BLOCK,
                    "Apenas professores podem adicionar ou modificar notas."
                )
        
        return (GuardrailResult.ALLOW, None)
    
    def _matches_any_pattern(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the patterns."""
        for pattern in patterns:
            # Replace {user_id} placeholder if present
            pattern = pattern.replace("{user_id}", str(self.user_id))
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False


class GuardrailPost:
    """
    Post-execution guardrail.
    Sanitizes responses to prevent data leakage.
    """
    
    def __init__(self, user_id: int, role: str):
        """
        Initialize guardrail with user context.
        
        Args:
            user_id: The requesting user's ID
            role: The user's role ('student' or 'teacher')
        """
        self.user_id = user_id
        self.role = role
    
    def sanitize(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize response to remove unauthorized data.
        
        For students, this ensures they can only see their own data
        even if the tool somehow returned more.
        
        Args:
            response: The tool response to sanitize
            
        Returns:
            Sanitized response
        """
        if self.role == "teacher":
            # Teachers can see everything
            return response
        
        # For students, filter out other students' data
        return self._filter_student_data(response)
    
    def _filter_student_data(self, data: Any) -> Any:
        """
        Recursively filter out data belonging to other students.
        
        Args:
            data: Data to filter
            
        Returns:
            Filtered data
        """
        if isinstance(data, dict):
            # Check if this is a grade/student record
            if "user_id" in data and data["user_id"] != self.user_id:
                return None  # Remove entirely
            
            if "student_id" in data and data["student_id"] != self.user_id:
                return None  # Remove entirely
            
            # Recursively filter nested structures
            filtered = {}
            for key, value in data.items():
                filtered_value = self._filter_student_data(value)
                if filtered_value is not None:
                    filtered[key] = filtered_value
            return filtered
        
        elif isinstance(data, list):
            filtered_list = []
            for item in data:
                filtered_item = self._filter_student_data(item)
                if filtered_item is not None:
                    filtered_list.append(filtered_item)
            return filtered_list
        
        return data


def check_pre_guardrail(
    user_id: int, 
    role: str, 
    message: str
) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to check pre-execution guardrail.
    
    Args:
        user_id: The requesting user's ID
        role: The user's role
        message: The user's message
        
    Returns:
        Tuple of (is_allowed, error_message if blocked)
    """
    guardrail = GuardrailPre(user_id, role)
    result, reason = guardrail.check(message)
    
    return (result == GuardrailResult.ALLOW, reason)


def sanitize_response(
    user_id: int,
    role: str,
    response: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convenience function to sanitize response.
    
    Args:
        user_id: The requesting user's ID
        role: The user's role
        response: The response to sanitize
        
    Returns:
        Sanitized response
    """
    guardrail = GuardrailPost(user_id, role)
    return guardrail.sanitize(response)
