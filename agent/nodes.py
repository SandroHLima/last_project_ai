"""
LangGraph nodes for the School Grades agent workflow.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session

from database import get_db_context, User, Disciplina, Turma
from tools import (
    get_user,
    add_grade,
    update_grade,
    get_grades_by_student,
    get_grade_summary,
    get_class_report,
    find_student_by_name,
    AuthorizationError,
    StudentAccessDenied,
    TeacherOnlyError,
    ValidationError,
    FeatureNotAvailableError,
)
from guardrails import check_pre_guardrail, sanitize_response
from .state import AgentState, Intent, REQUIRED_FIELDS
from .parser import get_parser


def load_user_context(state: AgentState) -> AgentState:
    """
    Node 1: Load user context from database.
    NEVER trust client-provided role.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with user context from DB
    """
    user_id = state["user_id"]
    
    with get_db_context() as db:
        try:
            user_info = get_user(db, user_id)
            state["role"] = user_info["role"]
            state["user_name"] = user_info["name"]
        except Exception as e:
            state["error"] = f"User not found: {str(e)}"
            state["blocked"] = True
            state["blocked_reason"] = "Utilizador não encontrado no sistema."
    
    return state


def guardrail_pre(state: AgentState) -> AgentState:
    """
    Node 2: Pre-execution guardrail.
    Detects and blocks obvious unauthorized requests.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with block status if needed
    """
    if state.get("blocked"):
        return state
    
    is_allowed, reason = check_pre_guardrail(
        user_id=state["user_id"],
        role=state["role"],
        message=state["message"]
    )
    
    if not is_allowed:
        state["blocked"] = True
        state["blocked_reason"] = reason
        state["intent"] = Intent.BLOCKED
    
    return state


def parse_intent_and_entities(state: AgentState) -> AgentState:
    """
    Node 3: Parse user message to extract intent and entities.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with intent and entities
    """
    if state.get("blocked"):
        return state
    
    parser = get_parser()
    intent, entities = parser.parse(
        message=state["message"],
        user_id=state["user_id"],
        role=state["role"],
        user_name=state.get("user_name", "")
    )
    
    state["intent"] = intent
    state["entities"] = entities
    
    # For students, always set student_id to their own ID for queries
    if state["role"] == "student" and intent in [Intent.QUERY_GRADES, Intent.SUMMARY]:
        state["entities"]["student_id"] = state["user_id"]
    
    return state


def check_missing_fields(state: AgentState) -> AgentState:
    """
    Node 3.5: Check if required fields are missing.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with missing_fields list
    """
    if state.get("blocked"):
        return state
    
    intent = state.get("intent", Intent.FALLBACK)
    entities = state.get("entities", {})
    
    if intent == Intent.FALLBACK:
        state["missing_fields"] = []
        state["ask_missing_fields"] = False
        return state
    
    required = REQUIRED_FIELDS.get(intent, [])
    missing = []
    
    for field in required:
        if field not in entities or entities[field] is None:
            # Check if we can resolve by name
            if field == "student_id" and "student_name" in entities:
                continue  # Will resolve in execute_tools
            if field == "disciplina_id" and "disciplina_name" in entities:
                continue  # Will resolve in execute_tools
            if field == "turma_id" and "turma_name" in entities:
                continue  # Will resolve in execute_tools
            missing.append(field)
    
    state["missing_fields"] = missing
    state["ask_missing_fields"] = len(missing) > 0
    
    return state


def resolve_names_to_ids(state: AgentState, db: Session) -> Dict[str, Any]:
    """
    Helper to resolve names to IDs.
    
    Args:
        state: Current agent state
        db: Database session
        
    Returns:
        Updated entities with resolved IDs
    """
    entities = state.get("entities", {}).copy()
    
    # Resolve student name to ID (teacher only)
    if "student_name" in entities and "student_id" not in entities:
        if state["role"] == "teacher":
            student = find_student_by_name(
                db, 
                state["user_id"], 
                entities["student_name"]
            )
            if student:
                entities["student_id"] = student["id"]
    
    # Resolve disciplina name to ID
    if "disciplina_name" in entities and "disciplina_id" not in entities:
        disciplina = (
            db.query(Disciplina)
            .filter(Disciplina.name.ilike(f"%{entities['disciplina_name']}%"))
            .first()
        )
        if disciplina:
            entities["disciplina_id"] = disciplina.id
    
    # Resolve turma name to ID
    if "turma_name" in entities and "turma_id" not in entities:
        turma = (
            db.query(Turma)
            .filter(Turma.name.ilike(f"%{entities['turma_name']}%"))
            .first()
        )
        if turma:
            entities["turma_id"] = turma.id
    
    return entities


def execute_tools(state: AgentState) -> AgentState:
    """
    Node 5: Execute the appropriate tool based on intent.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with tool result
    """
    if state.get("blocked"):
        return state
    
    if state.get("ask_missing_fields"):
        # Don't execute if fields are missing
        return state
    
    intent = state.get("intent", Intent.FALLBACK)
    
    with get_db_context() as db:
        try:
            # Resolve names to IDs
            entities = resolve_names_to_ids(state, db)
            
            if intent == Intent.ADD_GRADE:
                result = add_grade(
                    db=db,
                    teacher_id=state["user_id"],
                    student_id=entities.get("student_id"),
                    disciplina_id=entities.get("disciplina_id"),
                    turma_id=entities.get("turma_id"),
                    modulo=entities.get("modulo"),
                    descricao=entities.get("descricao"),
                    valor=entities.get("valor")
                )
                state["tool_result"] = result
            
            elif intent == Intent.UPDATE_GRADE:
                result = update_grade(
                    db=db,
                    teacher_id=state["user_id"],
                    grade_id=entities.get("grade_id"),
                    valor=entities.get("valor"),
                    modulo=entities.get("modulo"),
                    descricao=entities.get("descricao")
                )
                state["tool_result"] = result
            
            elif intent == Intent.QUERY_GRADES:
                student_id = entities.get("student_id", state["user_id"])
                result = get_grades_by_student(
                    db=db,
                    requester_id=state["user_id"],
                    student_id=student_id,
                    disciplina_id=entities.get("disciplina_id"),
                    modulo=entities.get("modulo"),
                    turma_id=entities.get("turma_id")
                )
                state["tool_result"] = result
            
            elif intent == Intent.SUMMARY:
                student_id = entities.get("student_id", state["user_id"])
                result = get_grade_summary(
                    db=db,
                    requester_id=state["user_id"],
                    student_id=student_id,
                    disciplina_id=entities.get("disciplina_id")
                )
                state["tool_result"] = result
            
            elif intent == Intent.CLASS_REPORT:
                result = get_class_report(
                    db=db,
                    requester_id=state["user_id"],
                    turma_id=entities.get("turma_id"),
                    disciplina_id=entities.get("disciplina_id"),
                    modulo=entities.get("modulo")
                )
                state["tool_result"] = result
            
            else:
                state["tool_result"] = None
        
        except StudentAccessDenied as e:
            state["error"] = "Não é possível aceder às notas de outros alunos."
            state["blocked"] = True
            state["blocked_reason"] = state["error"]
        
        except TeacherOnlyError as e:
            state["error"] = "Esta operação só pode ser realizada por um professor."
            state["blocked"] = True
            state["blocked_reason"] = state["error"]
        
        except ValidationError as e:
            state["error"] = f"Erro de validação: {e.message}"
        
        except FeatureNotAvailableError as e:
            state["error"] = "A eliminação de notas não é permitida no sistema."
            state["blocked"] = True
            state["blocked_reason"] = state["error"]
        
        except Exception as e:
            state["error"] = f"Erro ao executar operação: {str(e)}"
    
    return state


def guardrail_post(state: AgentState) -> AgentState:
    """
    Node 6: Post-execution guardrail.
    Sanitizes response to prevent data leakage.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with sanitized tool_result
    """
    if state.get("blocked") or not state.get("tool_result"):
        return state
    
    # Sanitize the result
    sanitized = sanitize_response(
        user_id=state["user_id"],
        role=state["role"],
        response=state["tool_result"]
    )
    
    state["tool_result"] = sanitized
    
    return state


def final_response(state: AgentState) -> AgentState:
    """
    Node 7: Generate final response.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with response
    """
    if state.get("blocked"):
        state["response"] = state.get("blocked_reason", "Pedido bloqueado.")
        return state
    
    if state.get("error"):
        state["response"] = state["error"]
        return state
    
    if state.get("ask_missing_fields"):
        missing = state.get("missing_fields", [])
        field_names = {
            "student_id": "aluno",
            "disciplina_id": "disciplina",
            "turma_id": "turma",
            "modulo": "módulo",
            "descricao": "descrição da avaliação",
            "valor": "valor da nota",
            "grade_id": "ID da nota"
        }
        missing_names = [field_names.get(f, f) for f in missing]
        state["response"] = f"Por favor, especifique: {', '.join(missing_names)}"
        return state
    
    intent = state.get("intent", Intent.FALLBACK)
    result = state.get("tool_result")
    
    if intent == Intent.FALLBACK:
        state["response"] = (
            "Posso ajudá-lo com:\n"
            "- Consultar notas\n"
            "- Ver médias e resumos\n"
            "- Adicionar notas (apenas professores)\n"
            "- Atualizar notas (apenas professores)\n"
            "- Relatórios de turma (apenas professores)"
        )
    elif result:
        state["response"] = _format_result(intent, result)
    else:
        state["response"] = "Operação concluída."
    
    return state


def _format_result(intent: Intent, result: Dict[str, Any]) -> str:
    """Format result for display."""
    if intent == Intent.ADD_GRADE:
        if result.get("success"):
            eval_data = result.get("evaluation", {})
            return (
                f"✓ Nota adicionada com sucesso!\n"
                f"Aluno: {eval_data.get('student_name')}\n"
                f"Disciplina: {eval_data.get('disciplina_name')}\n"
                f"Nota: {eval_data.get('valor')}"
            )
        return "Erro ao adicionar nota."
    
    elif intent == Intent.UPDATE_GRADE:
        if result.get("success"):
            return f"✓ Nota atualizada com sucesso!"
        return "Erro ao atualizar nota."
    
    elif intent == Intent.QUERY_GRADES:
        student = result.get("student", {})
        grades = result.get("grades", [])
        if not grades:
            return "Nenhuma nota encontrada."
        
        response = f"Notas de {student.get('name')}:\n"
        for g in grades[:10]:  # Limit to 10
            response += (
                f"• {g.get('disciplina_name')} - {g.get('descricao')}: "
                f"{g.get('valor')} ({g.get('modulo')})\n"
            )
        
        if len(grades) > 10:
            response += f"\n... e mais {len(grades) - 10} notas."
        
        return response
    
    elif intent == Intent.SUMMARY:
        student = result.get("student", {})
        avg = result.get("average")
        total = result.get("total_evaluations", 0)
        
        response = f"Resumo de {student.get('name')}:\n"
        response += f"Total de avaliações: {total}\n"
        response += f"Média geral: {avg if avg else 'N/A'}\n"
        
        by_disciplina = result.get("averages_by_disciplina", {})
        if by_disciplina:
            response += "\nMédias por disciplina:\n"
            for name, data in by_disciplina.items():
                response += f"• {name}: {data.get('average')}\n"
        
        return response
    
    elif intent == Intent.CLASS_REPORT:
        turma = result.get("turma", {})
        stats = result.get("class_statistics", {})
        students = result.get("students", [])
        
        response = f"Relatório da turma {turma.get('name')}:\n"
        response += f"Total de alunos: {len(students)}\n"
        
        if stats:
            response += f"Média da turma: {stats.get('mean', 'N/A')}\n"
        
        response += "\nAlunos:\n"
        for s in sorted(students, key=lambda x: x.get("average") or 0, reverse=True):
            avg = s.get("average")
            response += f"• {s.get('student_name')}: {avg if avg else 'N/A'}\n"
        
        return response
    
    return str(result)
