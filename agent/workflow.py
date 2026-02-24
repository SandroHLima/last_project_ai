"""
LangGraph workflow for the School Grades agent.
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, END

from .state import AgentState, Intent
from .nodes import (
    load_user_context,
    guardrail_pre,
    parse_intent_and_entities,
    check_missing_fields,
    execute_tools,
    guardrail_post,
    final_response,
)


def route_after_parsing(state: AgentState) -> str:
    if state.get("blocked"):
        return "blocked"
    
    if state.get("ask_missing_fields"):
        return "ask_fields"
    
    return "execute"


def route_after_execution(state: AgentState) -> str:
    if state.get("blocked"):
        return "blocked"
    
    return "sanitize"


def create_agent_graph() -> StateGraph:
    workflow = StateGraph(AgentState)
    
    workflow.add_node("load_user_context", load_user_context)
    workflow.add_node("guardrail_pre", guardrail_pre)
    workflow.add_node("parse_intent_and_entities", parse_intent_and_entities)
    workflow.add_node("check_missing_fields", check_missing_fields)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("guardrail_post", guardrail_post)
    workflow.add_node("final_response", final_response)
    
    workflow.set_entry_point("load_user_context")
    
    workflow.add_edge("load_user_context", "guardrail_pre")
    workflow.add_edge("guardrail_pre", "parse_intent_and_entities")
    workflow.add_edge("parse_intent_and_entities", "check_missing_fields")
    
    workflow.add_conditional_edges(
        "check_missing_fields",
        route_after_parsing,
        {
            "blocked": "final_response",
            "ask_fields": "final_response",
            "execute": "execute_tools"
        }
    )
    
    workflow.add_conditional_edges(
        "execute_tools",
        route_after_execution,
        {
            "blocked": "final_response",
            "sanitize": "guardrail_post"
        }
    )
    
    workflow.add_edge("guardrail_post", "final_response")
    workflow.add_edge("final_response", END)
    
    return workflow

_compiled_graph = None


def get_compiled_graph():
    """Get or create the compiled graph."""
    global _compiled_graph
    if _compiled_graph is None:
        workflow = create_agent_graph()
        _compiled_graph = workflow.compile()
    return _compiled_graph


def run_agent(user_id: int, message: str, show_all: bool = False) -> Dict[str, Any]:
    graph = get_compiled_graph()
    
    initial_state: AgentState = {
        "user_id": user_id,
        "message": message,
        "blocked": False,
        "ask_missing_fields": False,
        "show_all": bool(show_all),
    }
    
    final_state = graph.invoke(initial_state)
    
    return {
        "response": final_state.get("response", ""),
        "blocked": final_state.get("blocked", False),
        "intent": final_state.get("intent", Intent.FALLBACK).value if final_state.get("intent") else "fallback",
        "tool_result": final_state.get("tool_result"),
        "error": final_state.get("error"),
    }
