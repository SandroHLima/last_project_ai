"""
Unit tests for the School Grades system.
Tests authorization, guardrails, and tools.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, get_db_context, User, Disciplina, Turma, AlunoTurma, Avaliacao
from tools import (
    get_user,
    add_grade,
    update_grade,
    get_grades_by_student,
    get_grade_summary,
    get_class_report,
    AuthorizationService,
    StudentAccessDenied,
    TeacherOnlyError,
    ValidationError,
    InvalidUserError,
    FeatureNotAvailableError,
)
from guardrails import check_pre_guardrail, GuardrailPre, GuardrailResult


@pytest.fixture(scope="module")
def setup_database():
    """Set up test database."""
    init_db()
    
    with get_db_context() as db:
        # Clear existing data
        db.query(Avaliacao).delete()
        db.query(AlunoTurma).delete()
        db.query(User).delete()
        db.query(Disciplina).delete()
        db.query(Turma).delete()
        
        # Create test users
        teacher = User(id=1, name="Prof. Teste", role="teacher")
        student1 = User(id=2, name="Aluno Teste 1", role="student")
        student2 = User(id=3, name="Aluno Teste 2", role="student")
        db.add_all([teacher, student1, student2])
        
        # Create test disciplina and turma
        disciplina = Disciplina(id=1, name="Matemática Teste")
        turma = Turma(id=1, name="Teste-A")
        db.add_all([disciplina, turma])
        
        # Assign students to class
        db.add_all([
            AlunoTurma(user_id=2, turma_id=1),
            AlunoTurma(user_id=3, turma_id=1),
        ])
        
        db.commit()
    
    yield
    
    # Cleanup after tests
    with get_db_context() as db:
        db.query(Avaliacao).delete()
        db.query(AlunoTurma).delete()
        db.query(User).delete()
        db.query(Disciplina).delete()
        db.query(Turma).delete()


class TestAuthorization:
    """Tests for authorization service."""
    
    def test_get_user_role(self, setup_database):
        """Test getting user role from database."""
        with get_db_context() as db:
            auth = AuthorizationService(db)
            assert auth.get_user_role(1) == "teacher"
            assert auth.get_user_role(2) == "student"
    
    def test_invalid_user(self, setup_database):
        """Test error on invalid user."""
        with get_db_context() as db:
            auth = AuthorizationService(db)
            with pytest.raises(InvalidUserError):
                auth.get_user(9999)
    
    def test_teacher_enforcement(self, setup_database):
        """Test teacher-only enforcement."""
        with get_db_context() as db:
            auth = AuthorizationService(db)
            
            # Teacher should pass
            auth.enforce_teacher_only(1, "test_action")
            
            # Student should fail
            with pytest.raises(TeacherOnlyError):
                auth.enforce_teacher_only(2, "test_action")
    
    def test_student_data_access(self, setup_database):
        """Test student data access enforcement."""
        with get_db_context() as db:
            auth = AuthorizationService(db)
            
            # Teacher can access any student
            auth.enforce_student_data_access(1, 2)
            auth.enforce_student_data_access(1, 3)
            
            # Student can access own data
            auth.enforce_student_data_access(2, 2)
            
            # Student cannot access other student
            with pytest.raises(StudentAccessDenied):
                auth.enforce_student_data_access(2, 3)


class TestGuardrails:
    """Tests for guardrails."""
    
    def test_student_blocked_other_grades(self):
        """Test student blocked from accessing other students' grades."""
        guardrail = GuardrailPre(user_id=2, role="student")
        
        # Should be blocked
        result, _ = guardrail.check("Mostra as notas do João")
        assert result == GuardrailResult.BLOCK
        
        result, _ = guardrail.check("ver notas da Maria")
        assert result == GuardrailResult.BLOCK
    
    def test_student_allowed_own_grades(self):
        """Test student allowed to query own grades."""
        guardrail = GuardrailPre(user_id=2, role="student")
        
        result, _ = guardrail.check("Quero ver as minhas notas")
        assert result == GuardrailResult.ALLOW
        
        result, _ = guardrail.check("Qual é a minha média?")
        assert result == GuardrailResult.ALLOW
    
    def test_delete_blocked_for_all(self):
        """Test delete is blocked for everyone."""
        # For student
        guardrail = GuardrailPre(user_id=2, role="student")
        result, _ = guardrail.check("Apagar nota do teste")
        assert result == GuardrailResult.BLOCK
        
        # For teacher
        guardrail = GuardrailPre(user_id=1, role="teacher")
        result, _ = guardrail.check("Deletar avaliação 5")
        assert result == GuardrailResult.BLOCK
    
    def test_student_blocked_add_grade(self):
        """Test student blocked from adding grades."""
        guardrail = GuardrailPre(user_id=2, role="student")
        
        result, _ = guardrail.check("Adicionar nota 15 ao Pedro")
        assert result == GuardrailResult.BLOCK
    
    def test_teacher_allowed_all(self):
        """Test teacher allowed for all non-delete operations."""
        guardrail = GuardrailPre(user_id=1, role="teacher")
        
        result, _ = guardrail.check("Mostra as notas do João")
        assert result == GuardrailResult.ALLOW
        
        result, _ = guardrail.check("Adicionar nota 18 ao Miguel")
        assert result == GuardrailResult.ALLOW


class TestGradeTools:
    """Tests for grade tools."""
    
    def test_teacher_add_grade(self, setup_database):
        """Test teacher can add grade."""
        with get_db_context() as db:
            result = add_grade(
                db=db,
                teacher_id=1,
                student_id=2,
                disciplina_id=1,
                turma_id=1,
                modulo="Módulo Test",
                descricao="Teste Unit",
                valor=15.0
            )
            
            assert result["success"] == True
            assert result["evaluation"]["valor"] == 15.0
    
    def test_student_cannot_add_grade(self, setup_database):
        """Test student cannot add grade."""
        with get_db_context() as db:
            with pytest.raises(TeacherOnlyError):
                add_grade(
                    db=db,
                    teacher_id=2,  # Student ID
                    student_id=3,
                    disciplina_id=1,
                    turma_id=1,
                    modulo="Test",
                    descricao="Test",
                    valor=10.0
                )
    
    def test_student_query_own_grades(self, setup_database):
        """Test student can query own grades."""
        with get_db_context() as db:
            result = get_grades_by_student(
                db=db,
                requester_id=2,
                student_id=2
            )
            
            assert "grades" in result
            assert "student" in result
    
    def test_student_cannot_query_other_grades(self, setup_database):
        """Test student cannot query other student's grades."""
        with get_db_context() as db:
            with pytest.raises(StudentAccessDenied):
                get_grades_by_student(
                    db=db,
                    requester_id=2,
                    student_id=3
                )
    
    def test_teacher_query_any_student(self, setup_database):
        """Test teacher can query any student's grades."""
        with get_db_context() as db:
            result = get_grades_by_student(
                db=db,
                requester_id=1,
                student_id=2
            )
            assert "grades" in result
            
            result = get_grades_by_student(
                db=db,
                requester_id=1,
                student_id=3
            )
            assert "grades" in result


class TestReporting:
    """Tests for reporting tools."""
    
    def test_teacher_class_report(self, setup_database):
        """Test teacher can get class report."""
        with get_db_context() as db:
            result = get_class_report(
                db=db,
                requester_id=1,
                turma_id=1
            )
            
            assert "turma" in result
            assert "students" in result
            assert result["turma"]["id"] == 1
    
    def test_student_cannot_class_report(self, setup_database):
        """Test student cannot get class report."""
        with get_db_context() as db:
            with pytest.raises(TeacherOnlyError):
                get_class_report(
                    db=db,
                    requester_id=2,
                    turma_id=1
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
