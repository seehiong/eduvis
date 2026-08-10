"""
LangGraph Workflow Builder for Educational Generation Graph.
Supports native LangGraph StateGraph when langgraph is installed,
with a zero-dependency fallback state machine.
"""

from agent.schemas.graph_state import AgentGraphState
from agent.config import config
from agent.graph.nodes import (
    interpret_intent_node,
    enrich_context_node,
    generate_candidates_node,
    validate_eduvis_node,
    format_critique_node,
)

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


def should_continue(state: AgentGraphState) -> str:
    """
    Conditional edge router:
    - If valid: -> PASS (finish)
    - If invalid & retries remain: -> RETRY (format_critique -> generate_candidates)
    - If max retries exceeded: -> FAIL (stop)
    """
    if state.get("is_valid", False):
        return "pass"

    retry_count = state.get("retry_count", 0)
    if retry_count >= config.MAX_CRITIQUE_RETRIES:
        return "max_retries_exceeded"

    return "retry"


class EducationalGenerationGraph:
    """
    Fallback stateful execution graph implementing:
    Prompt -> Intent IR -> Context Enrichment -> Candidate Generation -> EduVis Validation -> Critique Loop
    """
    def __init__(self):
        self.nodes = {
            "interpret_intent": interpret_intent_node,
            "enrich_context": enrich_context_node,
            "generate_candidates": generate_candidates_node,
            "validate_eduvis": validate_eduvis_node,
            "format_critique": format_critique_node,
        }

    def run(self, initial_state: AgentGraphState) -> AgentGraphState:
        """
        Executes the graph pipeline deterministically.
        """
        state = dict(initial_state)

        # Step 1: Interpret Intent
        state = self.nodes["interpret_intent"](state)

        # Step 2: Enrich Context
        state = self.nodes["enrich_context"](state)

        # Step 3: Loop (Generate -> Validate -> Critique if needed)
        while True:
            state = self.nodes["generate_candidates"](state)
            state = self.nodes["validate_eduvis"](state)

            decision = should_continue(state)
            if decision == "pass":
                state["status"] = "success"
                break
            if decision == "max_retries_exceeded":
                state["status"] = "failed"
                break
            state = self.nodes["format_critique"](state)

        return state

    def invoke(self, initial_state: AgentGraphState) -> AgentGraphState:
        """Interface compatibility with LangGraph CompiledGraph.invoke()"""
        return self.run(initial_state)


def build_educational_generation_graph():
    """
    Factory function: returns native LangGraph StateGraph if langgraph is installed,
    otherwise returns zero-dependency EducationalGenerationGraph.
    """
    if LANGGRAPH_AVAILABLE:
        workflow = StateGraph(AgentGraphState)

        workflow.add_node("interpret_intent", interpret_intent_node)
        workflow.add_node("enrich_context", enrich_context_node)
        workflow.add_node("generate_candidates", generate_candidates_node)
        workflow.add_node("validate_eduvis", validate_eduvis_node)
        workflow.add_node("format_critique", format_critique_node)

        workflow.set_entry_point("interpret_intent")
        workflow.add_edge("interpret_intent", "enrich_context")
        workflow.add_edge("enrich_context", "generate_candidates")
        workflow.add_edge("generate_candidates", "validate_eduvis")

        workflow.add_conditional_edges(
            "validate_eduvis",
            should_continue,
            {
                "pass": END,
                "max_retries_exceeded": END,
                "retry": "format_critique"
            }
        )
        workflow.add_edge("format_critique", "generate_candidates")

        return workflow.compile()

    return EducationalGenerationGraph()
