"""Quick tests for the 4 bug fixes."""
from agent.state import Intent
from agent.parser import IntentEntityParser
from guardrails.guardrails import GuardrailPre, GuardrailResult


def test_bug1_self_referential_allowed():
    """Bug 1: 'minhas notas de matemática' should NOT be blocked."""
    g = GuardrailPre(user_id=3, role="student")
    result, _ = g.check("minhas notas de matemática")
    assert result == GuardrailResult.ALLOW


def test_bug2_notas_name_blocked():
    """Bug 2: 'Notas Sandro' should be blocked for a student."""
    g = GuardrailPre(user_id=3, role="student")
    result, _ = g.check("Notas Sandro")
    assert result == GuardrailResult.BLOCK


def test_bug2_lowercase_name_blocked():
    """Bug 2 variant: 'notas Sandro' also blocked."""
    g = GuardrailPre(user_id=3, role="student")
    result, _ = g.check("notas Sandro")
    assert result == GuardrailResult.BLOCK


def test_bug4_delete_intent_exists():
    """Bug 4: DELETE_GRADE intent must exist."""
    assert hasattr(Intent, "DELETE_GRADE")
    assert Intent.DELETE_GRADE.value == "delete_grade"


def test_bug4_rule_based_delete():
    """Bug 4: delete keywords map to DELETE_GRADE in rule-based parser."""
    p = IntentEntityParser()
    for word in ["apagar", "deletar", "remover", "excluir", "eliminar", "delete"]:
        intent, _ = p._rule_based_parse(f"{word} nota do teste", 1, "teacher")
        assert intent == Intent.DELETE_GRADE, f"'{word}' should map to DELETE_GRADE, got {intent}"


def test_disciplina_not_blocked():
    """'notas de matemática' and 'notas de física' should be allowed."""
    g = GuardrailPre(user_id=3, role="student")
    for subj in ["notas de matemática", "notas de física", "notas de português"]:
        result, _ = g.check(subj)
        assert result == GuardrailResult.ALLOW, f"'{subj}' should be allowed"


def test_other_student_still_blocked():
    """'notas do João' and 'notas da Ana' should be blocked for students."""
    g = GuardrailPre(user_id=3, role="student")
    for msg in ["notas do João", "notas da Ana", "ver notas do Pedro"]:
        result, _ = g.check(msg)
        assert result == GuardrailResult.BLOCK, f"'{msg}' should be blocked"


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  OK  {name}")
            except AssertionError as e:
                print(f"  FAIL {name}: {e}")
    print("\nDone.")
