"""
Intent and entity parser for the School Grades agent.
Uses LLM to extract structured information from user messages.
"""
import json
import re
from typing import Dict, Any, Optional, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

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

Responda APENAS em formato JSON válido:
{{
    "intent": "string (uma das intenções acima)",
    "entities": {{
        "campo": "valor"
    }},
    "confidence": "high/medium/low"
}}"""

    def __init__(self):
        """Initialize the parser with LLM."""
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0,
            api_key=settings.openai_api_key
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{message}")
        ])
        
        self.chain = self.prompt | self.llm | JsonOutputParser()
    
    def parse(
        self, 
        message: str, 
        user_id: int, 
        role: str, 
        user_name: str
    ) -> Tuple[Intent, Dict[str, Any]]:
        """
        Parse a message to extract intent and entities.
        
        Args:
            message: The user's message
            user_id: The user's ID
            role: The user's role
            user_name: The user's name
            
        Returns:
            Tuple of (intent, entities dict)
        """
        try:
            result = self.chain.invoke({
                "message": message,
                "user_id": user_id,
                "role": role,
                "user_name": user_name
            })
            
            intent_str = result.get("intent", "fallback")
            entities = result.get("entities", {})
            
            # Convert intent string to enum
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.FALLBACK
            
            # Clean up entities - convert string numbers to int/float
            cleaned_entities = self._clean_entities(entities)
            
            return intent, cleaned_entities
            
        except Exception as e:
            # Fallback to rule-based parsing if LLM fails
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
                    cleaned[key] = value  # Keep as string for name lookup
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
        """
        Fallback rule-based parsing when LLM fails.
        
        Args:
            message: The user's message
            user_id: The user's ID
            role: The user's role
            
        Returns:
            Tuple of (intent, entities)
        """
        message_lower = message.lower()
        entities = {}
        
        # Detect intent based on keywords
        if any(word in message_lower for word in ["adicionar", "inserir", "nova nota", "add"]):
            intent = Intent.ADD_GRADE
        elif any(word in message_lower for word in ["atualizar", "modificar", "alterar", "update", "mudar"]):
            intent = Intent.UPDATE_GRADE
        elif any(word in message_lower for word in ["média", "resumo", "summary", "médias"]):
            intent = Intent.SUMMARY
        elif any(word in message_lower for word in ["relatório", "report", "turma"]) and role == "teacher":
            intent = Intent.CLASS_REPORT
        elif any(word in message_lower for word in ["nota", "notas", "grades", "avaliação", "avaliações"]):
            intent = Intent.QUERY_GRADES
        else:
            intent = Intent.FALLBACK
        
        # Extract entities with regex
        # Note value (0-20)
        valor_match = re.search(r'\b(\d{1,2}(?:[.,]\d+)?)\s*(?:valores?|pontos?)?\b', message)
        if valor_match:
            try:
                entities["valor"] = float(valor_match.group(1).replace(",", "."))
            except ValueError:
                pass
        
        # Module
        modulo_match = re.search(r'(módulo|capítulo|module)\s*(\d+|[IVX]+)', message_lower)
        if modulo_match:
            entities["modulo"] = f"Módulo {modulo_match.group(2)}"
        
        # Turma
        turma_match = re.search(r'turma\s+(\d+[A-Za-z]?)', message_lower)
        if turma_match:
            entities["turma_name"] = turma_match.group(1).upper()
        
        # If student asking for their own grades
        if role == "student" and intent in [Intent.QUERY_GRADES, Intent.SUMMARY]:
            entities["student_id"] = user_id
        
        return intent, entities


# Singleton instance
_parser_instance = None


def get_parser() -> IntentEntityParser:
    """Get or create parser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = IntentEntityParser()
    return _parser_instance
