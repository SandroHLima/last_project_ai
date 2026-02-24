"""
Intent and entity parser for the School Grades agent.
Uses LLM to extract structured information from user messages.
"""
import json
import re
from typing import Dict, Any, Optional, Tuple
try:
    from langchain_community.chat_models import ChatOllama
except Exception:
    ChatOllama = None
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from config import settings
from .state import Intent, Entities


class IntentEntityParser:
    """
    Parser that uses LLM to extract intent and entities from user messages.
    """
    
    SYSTEM_PROMPT = """Você é um assistente especializado em analisar mensagens sobre notas e avaliações escolares.

Sua tarefa é extrair a INTENÇÃO e as ENTIDADES de uma mensagem do usuário.

INTENÇÕES POSSÍVEIS:
- add_grade: Professor quer adicionar uma nova nota
- update_grade: Professor quer atualizar/modificar uma nota existente
- delete_grade: Apagar/eliminar/remover uma nota ou avaliação
- query_grades: Consultar notas (professor ou aluno)
- summary: Ver resumo/médias de notas
- class_report: Professor quer relatório de turma
- fallback: Mensagem não relacionada a notas ou não compreendida

ENTIDADES A EXTRAIR (quando presentes):
- student_id: ID do aluno (número)
- student_name: Nome do aluno mencionado
- grade_id: ID da nota a atualizar (número)
- valor: Valor da nota (número 0-20)
- disciplina_id: ID da disciplina (número)
- disciplina_name: Nome da disciplina mencionada
- turma_id: ID da turma (número)
- turma_name: Nome da turma mencionada (ex: "10A", "11B")
- modulo: Módulo (ex: "Módulo 1", "Capítulo 2")
- descricao: Descrição da avaliação (ex: "Teste 1", "Projeto")

CONTEXTO DO USUÁRIO:
- user_id: {user_id}
- role: {role}
- name: {user_name}

Se o usuário é aluno e pede "minhas notas", o student_id deve ser o próprio user_id.
Se o usuário menciona outro aluno por nome, extraia o student_name.

Responda APENAS em formato JSON válido, sem explicações:
{{
    "intent": "string (uma das intenções acima)",
    "entities": {{
        "campo": "valor"
    }},
    "confidence": "high/medium/low"
}}
/no_think"""

    def __init__(self):
        """Initialize the parser with LLM (Ollama / Qwen3)."""
        self.llm = ChatOllama(
            model=settings.ollama_model,
            temperature=0,
            base_url=settings.ollama_base_url,
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{message}")
        ])
        
        # Use StrOutputParser so we can strip <think> tags before JSON parsing
        self._raw_chain = self.prompt | self.llm | StrOutputParser()

    @staticmethod
    def _strip_think_tags(text: str) -> str:
        """Remove <think>...</think> blocks that qwen3 may emit."""
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()
    
    def parse(
        self, 
        message: str, 
        user_id: int, 
        role: str, 
        user_name: str
    ) -> Tuple[Intent, Dict[str, Any]]:
        lower = message.lower().strip()
        simple_triggers = ["minhas notas", "minha nota", "mostra as", "mostra", "ver as", "ver minhas", "minhas", "minha"]
        if len(message) < 120 and any(t in lower for t in simple_triggers):
            return self._rule_based_parse(message, user_id, role)

        try:
            raw = self._raw_chain.invoke({
                "message": message,
                "user_id": user_id,
                "role": role,
                "user_name": user_name
            })
            clean = self._strip_think_tags(raw)
            result = json.loads(clean)
            
            intent_str = result.get("intent", "fallback")
            entities = result.get("entities", {})
            
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.FALLBACK
            
            cleaned_entities = self._clean_entities(entities)
            
            return intent, cleaned_entities
            
        except Exception as e:
            return self._rule_based_parse(message, user_id, role)
    
    def _clean_entities(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and convert entity values."""
        cleaned = {}
        
        int_fields = ["student_id", "grade_id", "disciplina_id", "turma_id"]
        float_fields = ["valor"]
        
        for key, value in entities.items():
            if value is None or value == "":
                continue
            
            if key in int_fields:
                try:
                    cleaned[key] = int(value)
                except (ValueError, TypeError):
                    cleaned[key] = value
            elif key in float_fields:
                try:
                    cleaned[key] = float(value)
                except (ValueError, TypeError):
                    pass
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _rule_based_parse(
        self, 
        message: str, 
        user_id: int, 
        role: str
    ) -> Tuple[Intent, Dict[str, Any]]:
        msg = message
        msg_lower = msg.lower()
        entities: Dict[str, Any] = {}

        # --- Detect intent ---
        if any(w in msg_lower for w in ["apagar", "deletar", "delete", "remover", "excluir", "eliminar"]):
            intent = Intent.DELETE_GRADE
        elif any(w in msg_lower for w in ["adicionar", "inserir", "nova nota", "add", "lançar", "registar", "registrar"]):
            intent = Intent.ADD_GRADE
        elif any(w in msg_lower for w in ["atualizar", "modificar", "alterar", "update", "mudar"]):
            intent = Intent.UPDATE_GRADE
        elif any(w in msg_lower for w in ["média", "resumo", "summary", "médias"]):
            intent = Intent.SUMMARY
        elif any(w in msg_lower for w in ["relatório", "report"]) or ("turma" in msg_lower and role == "teacher" and not any(w in msg_lower for w in ["adicionar","inserir","nota"])):
            intent = Intent.CLASS_REPORT
        elif any(w in msg_lower for w in ["nota", "notas", "grades", "avaliação", "avaliações"]):
            intent = Intent.QUERY_GRADES
        else:
            intent = Intent.FALLBACK

        valor_match = re.search(r'\b(\d{1,2}(?:[.,]\d+)?)\s*(?:valores?|pontos?)?\b', msg)
        if valor_match:
            try:
                entities["valor"] = float(valor_match.group(1).replace(",", "."))
            except ValueError:
                pass

        modulo_match = re.search(r'(?:módulo|modulo|capítulo|module)\s*(\d+|[IVX]+)', msg_lower)
        if modulo_match:
            entities["modulo"] = f"Módulo {modulo_match.group(1)}"

        turma_match = re.search(r'turma\s+(\d+[A-Za-z]?)', msg_lower)
        if turma_match:
            entities["turma_name"] = turma_match.group(1).upper()

        student_match = re.search(r'(?:aluno|aluna|estudante)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)', msg)
        if student_match:
            entities["student_name"] = student_match.group(1)

        disc_match = re.search(
            r'(?:disciplina|em|de)\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)',
            msg
        )
        if disc_match:
            candidate = disc_match.group(1)
            if "student_name" not in entities or candidate.lower() != entities["student_name"].lower():
                entities["disciplina_name"] = candidate

        desc_match = re.search(
            r'(teste\s*\w*|exame\s*\w*|projeto\s*\w*|trabalho\s*\w*|prova\s*\w*)',
            msg_lower
        )
        if desc_match:
            entities["descricao"] = desc_match.group(1).strip().title()

        if role == "student" and intent in [Intent.QUERY_GRADES, Intent.SUMMARY]:
            entities["student_id"] = user_id

        return intent, entities

_parser_instance = None


def get_parser() -> IntentEntityParser:
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = IntentEntityParser()
    return _parser_instance
