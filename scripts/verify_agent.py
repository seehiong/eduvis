"""
EduVis Agent End-to-End Verification Script
============================================
PURPOSE: Prove that the 3-stage pipeline works:
  Stage 1 → Ollama LLM generates raw candidate questions
  Stage 2 → EduVis Core blueprint engine assembles them into a paper
  Stage 3 → Coverage validator confirms marks & concept alignment

SUCCESS CRITERIA:
  - Status = "success"
  - Is Valid = True
  - Sample Question 1 shows a real, curriculum-aligned question (NOT a placeholder)
  - OLLAMA RAW LLM RESPONSE shows actual question JSON from the model

If "Sample Question 1" reads "Evaluate question N involving ...", that means
the LLM failed and the DETERMINISTIC FALLBACK fired. The pipeline still
passes validation, but NO real LLM intelligence was used.
"""

import httpx
from agent.config import config
from agent.graph.workflow import build_educational_generation_graph
from agent.graph.nodes import call_ollama_llm, get_available_ollama_model

DIVIDER = "=" * 60

# ---------------------------------------------------------------------------
# 0. Infrastructure Check
# ---------------------------------------------------------------------------
print(f"\n{DIVIDER}")
print("STEP 0: Infrastructure Check")
print(DIVIDER)

ollama_online = False
installed_models = []
try:
    resp = httpx.get(f"{config.OLLAMA_BASE_URL.rstrip('/')}/", timeout=3.0)
    ollama_online = resp.status_code == 200
    tags_resp = httpx.get(f"{config.OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=3.0)
    if tags_resp.status_code == 200:
        installed_models = [m.get("name") for m in tags_resp.json().get("models", []) if isinstance(m, dict)]
except Exception as exc:
    print(f"  Ollama Ping Error: {exc}")

target_model = get_available_ollama_model()
print(f"  Ollama URL     : {config.OLLAMA_BASE_URL}")
print(f"  Ollama Online  : {ollama_online}")
print(f"  Target Model   : {target_model}")
print(f"  Installed Models ({len(installed_models)}): {', '.join(installed_models[:5])}{'...' if len(installed_models) > 5 else ''}")

# ---------------------------------------------------------------------------
# 1. Direct LLM Smoke Test
# ---------------------------------------------------------------------------
print(f"\n{DIVIDER}")
print("STEP 1: Direct Ollama LLM Smoke Test")
print("  (Proves the model is loaded and responding before we run the full graph)")
print(DIVIDER)

direct_response, direct_err = call_ollama_llm('Say hello in JSON format like: {"greeting": "hello"}')
if direct_response:
    print("  Result  : SUCCESS")
    print(f"  Response: {direct_response[:150]}")
else:
    print(f"  Result  : FAILED — {direct_err}")
    print("  WARNING: Ollama is not responding. The graph will use deterministic fallback only.")

# ---------------------------------------------------------------------------
# 2. Graph Invocation — Full 3-Stage Pipeline
# ---------------------------------------------------------------------------
print(f"\n{DIVIDER}")
print("STEP 2: Running Full Agent Graph (3-Stage Pipeline)")
print("  Stage 1: Intent parsing  → what subject, topic, marks budget?")
print("  Stage 2: LLM generation  → Ollama produces 10 candidate questions")
print("  Stage 3: EduVis Core     → blueprint assembly + coverage validation")
print("  (Watch for [DEBUG] lines — they trace each graph node invocation)")
print(DIVIDER)

SAMPLE_CURRICULUM_YAML = """
schema_version: "1.0"
concepts:
  - code: "negative_numbers"
    name: "Negative Numbers"
    exam_weight: 1.0
skills:
  - code: "order_integers"
    name: "Ordering negative numbers"
    concept: "negative_numbers"
"""

graph = build_educational_generation_graph()
result = graph.invoke({
    "user_prompt": "Create a 60-mark paper on negative numbers",
    "curriculum_yaml": SAMPLE_CURRICULUM_YAML,
    "retry_count": 0,
    "critique_history": []
})

# ---------------------------------------------------------------------------
# 3. Verification Proof
# ---------------------------------------------------------------------------
print(f"\n{DIVIDER}")
print("STEP 3: Verification Proof")
print(DIVIDER)

status      = result.get("status")
is_valid    = result.get("is_valid")
intent      = result.get("intent")
candidates  = result.get("candidate_questions", [])
raw_llm     = result.get("raw_llm_response")
llm_err     = result.get("llm_error")
val_errors  = result.get("validation_errors", [])
retry_count = result.get("retry_count", 0)

print(f"  Pipeline Status      : {status}")
print(f"  Is Valid             : {is_valid}")
print(f"  Retries Used         : {retry_count}")
print(f"  Target Subject       : {intent.subject if intent else 'N/A'}")
print(f"  Target Topic         : {intent.topic if intent else 'N/A'}")
print(f"  Marks Budget         : {intent.total_marks if intent else 'N/A'}")
print(f"  Questions Generated  : {len(candidates)}")

# Detect whether questions are real LLM output or deterministic fallback
fallback_stems = [q for q in candidates if "Evaluate question" in (q.get("stem") or "")]
llm_stems      = [q for q in candidates if "Evaluate question" not in (q.get("stem") or "")]
print(f"  LLM-sourced questions: {len(llm_stems)}")
print(f"  Fallback questions   : {len(fallback_stems)}")

if len(llm_stems) == len(candidates) and candidates:
    print("\n  ✅ ALL QUESTIONS ARE REAL LLM OUTPUT — Pipeline fully working!")
elif llm_stems:
    print(f"\n  ⚠️  MIXED: {len(llm_stems)} real LLM + {len(fallback_stems)} fallback questions.")
else:
    print("\n  ❌ ALL QUESTIONS ARE FALLBACK — LLM did not generate usable output this run.")
    print("     (This is expected if Ollama returned inconsistent JSON. Retry to try again.)")

print("\n--- OLLAMA RAW LLM RESPONSE (last successful call) ---")
if raw_llm:
    display = raw_llm[:600] + "..." if len(raw_llm) > 600 else raw_llm
    print(display)
else:
    print(f"  (No response captured — Diagnostics: {llm_err})")

print("\n--- VALIDATION ERRORS / WARNINGS ---")
if val_errors:
    for err in val_errors:
        print(f"  * {err}")
else:
    print("  (None — 100% Valid)")

print("\n--- SAMPLE QUESTIONS ---")
for i, q in enumerate(candidates[:3], 1):
    stem = q.get("stem") or q.get("prompt") or "N/A"
    marks = q.get("marks", "?")
    is_fallback = "Evaluate question" in stem
    tag = " [FALLBACK]" if is_fallback else " [LLM ✅]"
    print(f"  Q{i} ({marks}m){tag}: {stem[:120]}")

if not candidates:
    print("  (No questions generated)")

print(f"\n{DIVIDER}")
if status == "success" and is_valid and llm_stems:
    print("RESULT: ✅ FULL SUCCESS — Ollama LLM + EduVis Core pipeline verified end-to-end.")
elif status == "success" and is_valid:
    print("RESULT: ⚠️  PARTIAL — Pipeline succeeded but used deterministic fallback, not LLM output.")
    print("  The LLM is running but its JSON format varied. Re-run to try again.")
else:
    print("RESULT: ❌ PIPELINE DID NOT REACH SUCCESS STATUS.")
print(DIVIDER)
