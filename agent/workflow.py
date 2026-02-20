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
    """
    Routing function to determine next step after parsing.
    
    Routes to:
    - "blocked" if request was blocked
    - "ask_fields" if required fields are missing
    - "execute" otherwise
    """
    if state.get("blocked"):
        return "blocked"
    
    if state.get("ask_missing_fields"):
        return "ask_fields"
    
    return "execute"


def route_after_execution(state: AgentState) -> str:
    """
    Routing function to determine next step after execution.
    
    Routes to:
    - "blocked" if an error occurred that blocked the request
    - "sanitize" otherwise
    """
    if state.get("blocked"):
        return "blocked"
    
    return "sanitize"


def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph workflow for the agent.
    
    Workflow:
    1. load_user_context - Load role from DB
    2. guardrail_pre - Check for obvious unauthorized requests
    3. parse_intent_and_entities - Extract intent and entities
    4. check_missing_fields - Validate required fields
    5. route - Conditional routing
    6. execute_tools - Execute the appropriate tool
    7. guardrail_post - Sanitize response
    8. final_response - Generate response
    
    Returns:
        Compiled StateGraph
    """
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("load_user_context", load_user_context)
    workflow.add_node("guardrail_pre", guardrail_pre)
    workflow.add_node("parse_intent_and_entities", parse_intent_and_entities)
    workflow.add_node("check_missing_fields", check_missing_fields)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("guardrail_post", guardrail_post)
    workflow.add_node("final_response", final_response)
    
    # Define edges
    workflow.set_entry_point("load_user_context")
    
    workflow.add_edge("load_user_context", "guardrail_pre")
    workflow.add_edge("guardrail_pre", "parse_intent_and_entities")
    workflow.add_edge("parse_intent_and_entities", "check_missing_fields")
    
    # Conditional routing after checking fields
    workflow.add_conditional_edges(
        "check_missing_fields",
        route_after_parsing,
        {
            "blocked": "final_response",
            "ask_fields": "final_response",
            "execute": "execute_tools"
        }
    )
    
    # Conditional routing after execution
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


# Create and compile the graph once
_compiled_graph = None


def get_compiled_graph():
    """Get or create the compiled graph."""
    global _compiled_graph
    if _compiled_graph is None:
        workflow = create_agent_graph()
        _compiled_graph = workflow.compile()
    return _compiled_graph


def run_agent(user_id: int, message: str) -> Dict[str, Any]:
    """
    Run the agent with a user message.
    
    Args:
        user_id: The ID of the requesting user
        message: The user's message
        
    Returns:
        Dictionary with response and status
    """
    graph = get_compiled_graph()
    
    # Initialize state
    initial_state: AgentState = {
        "user_id": user_id,
        "message": message,
        "blocked": False,
        "ask_missing_fields": False,
    }
    
    # Run the graph
    final_state = graph.invoke(initial_state)
    
    return {
        "response": final_state.get("response", ""),
        "blocked": final_state.get("blocked", False),
        "intent": final_state.get("intent", Intent.FALLBACK).value if final_state.get("intent") else "fallback",
        "tool_result": final_state.get("tool_result"),
        "error": final_state.get("error"),
    }
