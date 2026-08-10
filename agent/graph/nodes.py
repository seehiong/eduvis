"""
Node functions for the Educational Generation Graph.
Each node processes AgentGraphState and returns updated state fields.
"""

import json
from typing import Any, Dict, List
from agent.schemas.graph_state import AgentGraphState
from agent.schemas.intent import GenerationIntent
from agent.tools.curriculum_tools import inspect_curriculum, check_prerequisites
from agent.tools.paper_tools import assemble_paper_from_intent
from agent.config import config


def interpret_intent_node(state: AgentGraphState) -> AgentGraphState:
    """
    Node 1: Interprets user prompt into a structured GenerationIntent IR.
    """
    user_prompt = state.get("user_prompt", "")

    # Fallback/heuristic intent extraction (or via local LLM completion)
    intent = GenerationIntent(
        topic="negative_numbers" if "negative" in user_prompt.lower() else "general_math",
        target_concepts=["concept_1"],
        total_marks=60,
        question_count=10,
        difficulty_target="medium"
    )

    return {
        **state,
        "intent": intent,
        "status": "intent_interpreted"
    }


def enrich_context_node(state: AgentGraphState) -> AgentGraphState:
    """
    Node 2: Enriches context using EduVis Core graph inspection & prerequisite checking.
    """
    curr_yaml = state.get("curriculum_yaml", "")
    intent = state.get("intent")

    if not curr_yaml:
        return {
            **state,
            "status": "error",
            "validation_errors": ["No curriculum_yaml provided in graph state."]
        }

    curr_info = inspect_curriculum(curr_yaml)
    target_codes = intent.target_concepts if intent else []
    prereq_info = check_prerequisites(curr_yaml, target_codes)

    return {
        **state,
        "resolved_concepts": curr_info.get("concepts", []),
        "resolved_prerequisites": prereq_info.get("required_prerequisites", []),
        "curriculum_graph_context": curr_info,
        "status": "context_enriched"
    }


def get_available_ollama_model() -> str:
    """Queries Ollama /api/tags to find an available model, matching config or picking first installed."""
    try:
        import httpx
        url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/api/tags"
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", []) if isinstance(m, dict)]
                if config.MODEL_DEFAULT in models:
                    return config.MODEL_DEFAULT
                if models:
                    # Pick closest match or first available model tag
                    for m in models:
                        if "qwen" in m.lower():
                            return m
                    return models[0]
    except Exception:
        pass
    return config.MODEL_DEFAULT


def call_ollama_llm(prompt: str, system_prompt: str = "", question_count: int = 10) -> tuple[str | None, str | None]:
    """
    Invokes local Ollama LLM inference service if available.
    Returns (response_text, error_message).

    Uses Ollama structured output (JSON Schema) to force the model to output
    exactly {"questions": [...N items...]} — bypassing free-form JSON variation.
    """
    try:
        import httpx
        target_model = get_available_ollama_model()

        chat_url = f"{config.OLLAMA_BASE_URL.rstrip('/')}/api/chat"

        # JSON Schema forces the model to output exactly the required structure.
        # Without this, qwen3.5:9b invents its own keys and almost always
        # returns a single-question object instead of a list.
        output_schema = {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "stem":   {"type": "string"},
                            "answer": {"type": "string"}
                        },
                        "required": ["stem", "answer"]
                    },
                    "minItems": question_count,
                    "maxItems": question_count
                }
            },
            "required": ["questions"]
        }

        chat_payload = {
            "model": target_model,
            "think": False,         # Top-level flag — suppresses Qwen3.x chain-of-thought
            "stream": False,
            "format": output_schema,   # Structured output: forces {"questions": [...]}
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt or (
                        f"You are an educational item author. "
                        f"Generate exactly {question_count} unique assessment questions. "
                        f"Each question object must have: stem (the question text) and answer (the correct answer). "
                        f"Make questions progressively harder. Use clear, concise language."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "options": {
                "num_predict": 900      # Enough for 10 questions × ~90 tokens each
            }
        }
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(chat_url, json=chat_payload)
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get("message", {})
                msg_content = (msg.get("content") or "").strip()
                msg_thinking = (msg.get("thinking") or "").strip()
                text = msg_content or msg_thinking
                if text:
                    return text, None
                return None, f"Ollama returned empty message. done_reason={data.get('done_reason')} eval_count={data.get('eval_count')}"
            return None, f"Ollama HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as exc:
        return None, f"Ollama Connection Error: {str(exc)}"


def extract_json_payload(text: str) -> Any:
    """Extracts valid JSON payload from LLM text output even if prefixed by chain-of-thought reasoning."""
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    import re
    # Match markdown json block ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    # Match raw outer JSON array [...] or object {...}
    match = re.search(r"(\[\s*\{[\s\S]*\}\s*\]|\{[\s\S]*\})", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except Exception:
            pass

    return None


def _resolve_target_concept(state: AgentGraphState, intent: Any) -> str:
    resolved_concepts = state.get("resolved_concepts", [])
    if resolved_concepts and isinstance(resolved_concepts, list) and len(resolved_concepts) > 0:
        first = resolved_concepts[0]
        if isinstance(first, dict) and "code" in first:
            return first["code"]
    if intent and intent.target_concepts:
        return intent.target_concepts[0]
    return "negative_numbers"


def _parse_llm_candidates(llm_response: str, concept_code: str, marks_per_item: int) -> List[Dict[str, Any]]:
    try:
        parsed = extract_json_payload(llm_response)
        print(f"[DEBUG] Parsed type: {type(parsed).__name__}, value snippet: {str(parsed)[:100]}")
        if isinstance(parsed, list):
            parsed_list = parsed
        elif isinstance(parsed, dict):
            parsed_list = (
                parsed.get("questions")
                or parsed.get("question_list")
                or parsed.get("items")
                or parsed.get("candidate_questions")
                or []
            )
            if not parsed_list and parsed.get("stem"):
                parsed_list = [parsed]
        else:
            parsed_list = []

        candidates = []
        for idx, q in enumerate(parsed_list, 1):
            if not isinstance(q, dict):
                q = {"stem": str(q)}
            obj = "conceptual_understanding" if idx <= 4 else ("procedural_fluency" if idx <= 8 else "application")
            candidates.append({
                "id": f"q_{idx}",
                "type": "short_answer",
                "concept": concept_code,
                "concepts": [concept_code],
                "marks": marks_per_item,
                "prompt": q.get("prompt") or q.get("stem") or q.get("question") or f"Question {idx}",
                "stem": q.get("stem") or q.get("prompt") or q.get("question") or f"Evaluate question {idx} involving {concept_code}.",
                "placement": {
                    "assessment_objective": obj,
                    "difficulty": "medium",
                    "lesson_phase": "independent_practice"
                },
                "assessment_objective": obj
            })
        return candidates
    except Exception as e:
        print(f"[DEBUG] Exception parsing LLM response: {e}")
        return []


def _build_fallback_candidates(question_count: int, concept_code: str, marks_per_item: int, topic: str) -> List[Dict[str, Any]]:
    candidates = []
    for i in range(1, question_count + 1):
        obj = "conceptual_understanding" if i <= 4 else ("procedural_fluency" if i <= 8 else "application")
        candidates.append({
            "id": f"q_{i}",
            "type": "short_answer",
            "concept": concept_code,
            "concepts": [concept_code],
            "marks": marks_per_item,
            "prompt": f"Practice Question {i} on {topic}",
            "stem": f"Evaluate question {i} involving {concept_code}.",
            "placement": {
                "assessment_objective": obj,
                "difficulty": "medium",
                "lesson_phase": "independent_practice"
            },
            "assessment_objective": obj
        })
    return candidates


def generate_candidates_node(state: AgentGraphState) -> AgentGraphState:
    """
    Node 3: Generates candidate question elements or lesson cards using local Ollama model if online,
    or structured candidate generator with deterministic blueprint matching.
    """
    intent = state.get("intent")
    retry_count = state.get("retry_count", 0)
    concept_code = _resolve_target_concept(state, intent)

    question_count = intent.question_count if intent else 10
    total_marks = intent.total_marks if intent else 60
    marks_per_item = total_marks // question_count if question_count > 0 else 6

    # 1. Attempt real local Ollama LLM call with structured JSON schema output
    llm_prompt = f"Generate {question_count} assessment questions for concept '{concept_code}' with total marks {total_marks}."
    print(f"[DEBUG] Calling Ollama | count={question_count} | concept='{concept_code}' | marks={total_marks}")
    llm_response, llm_error = call_ollama_llm(llm_prompt, question_count=question_count)
    print(f"[DEBUG] Ollama response length: {len(llm_response) if llm_response else 0} | error: {llm_error}")
    if llm_response:
        print(f"[DEBUG] Raw LLM snippet: {llm_response[:200]}")

    candidates = _parse_llm_candidates(llm_response, concept_code, marks_per_item) if llm_response else []

    # 2. Fallback candidate generation if Ollama is unreachable or returned unparseable JSON
    if not candidates:
        topic_name = intent.topic if intent else "topic"
        candidates = _build_fallback_candidates(question_count, concept_code, marks_per_item, topic_name)

    return {
        **state,
        "candidate_questions": candidates,
        # Preserve previous raw_llm_response if this call timed out
        "raw_llm_response": llm_response if llm_response else state.get("raw_llm_response"),
        "llm_error": llm_error if llm_response is None else None,
        "retry_count": retry_count,
        "status": "candidates_generated"
    }


def validate_eduvis_node(state: AgentGraphState) -> AgentGraphState:
    """
    Node 4: Deterministically validates candidate items using EduVis Core validators.
    """
    curr_yaml = state.get("curriculum_yaml", "")
    intent = state.get("intent")
    candidates = state.get("candidate_questions", [])

    if intent and candidates:
        assembly_result = assemble_paper_from_intent(curr_yaml, intent, candidates)
        is_valid = assembly_result.get("is_valid", False)
        errors = assembly_result.get("coverage_warnings", [])
        # Surface any hidden exception from blueprint assembly
        if assembly_result.get("status") == "error":
            print(f"[DEBUG] assemble_paper_from_intent EXCEPTION: {assembly_result.get('message')}")
        else:
            print(f"[DEBUG] assemble_paper_from_intent OK | is_valid={is_valid} | warnings={len(errors)}")
    else:
        is_valid = False
        errors = ["Missing intent or candidate questions."]

    return {
        **state,
        "is_valid": is_valid,
        "validation_errors": errors,
        "status": "success" if is_valid else "validated"
    }


def format_critique_node(state: AgentGraphState) -> AgentGraphState:
    """
    Node 5: Formats compilation & coverage errors into critique feedback for candidate retry.
    """
    errors = state.get("validation_errors", [])
    retry_count = state.get("retry_count", 0)
    history = state.get("critique_history", [])

    critique_msg = f"Attempt {retry_count + 1} validation feedback: " + "; ".join(errors)
    history.append(critique_msg)

    return {
        **state,
        "critique_history": history,
        "retry_count": retry_count + 1,
        "status": "critiqued"
    }
