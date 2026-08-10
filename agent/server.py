"""
FastAPI Server for EduVis Agent Service.
Provides REST endpoints for Studio UI integration and agentic generation pipelines.
"""

from typing import Optional
from pydantic import BaseModel

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from agent.config import config
from agent.schemas.graph_state import AgentGraphState
from agent.graph.workflow import build_educational_generation_graph
from agent.tools.validator_tools import validate_generated_spec


class GeneratePaperRequest(BaseModel):
    prompt: str
    curriculum_yaml: str
    target_marks: Optional[int] = 60
    model: Optional[str] = None


class ValidateSpecRequest(BaseModel):
    yaml_text: str
    spec_type: Optional[str] = "auto"


if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="EduVis Agent API",
        description="Agentic Generation API for EduVis v1.3",
        version="1.3.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health_check():
        return {
            "status": "healthy",
            "version": "1.3.0",
            "ollama_url": config.OLLAMA_BASE_URL,
            "default_model": config.MODEL_DEFAULT
        }

    @app.post("/api/generate/paper")
    def generate_paper_endpoint(req: GeneratePaperRequest):
        graph = build_educational_generation_graph()
        initial_state: AgentGraphState = {
            "user_prompt": req.prompt,
            "curriculum_yaml": req.curriculum_yaml,
            "retry_count": 0,
            "critique_history": [],
            "is_valid": False
        }
        result = graph.invoke(initial_state)
        return {
            "status": result.get("status"),
            "intent": result.get("intent").model_dump() if hasattr(result.get("intent"), "model_dump") else (result.get("intent").dict() if result.get("intent") else None),
            "candidate_questions": result.get("candidate_questions"),
            "validation_errors": result.get("validation_errors"),
            "critique_history": result.get("critique_history"),
        }

    @app.post("/api/validate")
    def validate_endpoint(req: ValidateSpecRequest):
        res = validate_generated_spec(req.yaml_text, req.spec_type)
        return res

else:
    app = None


def main():
    if not FASTAPI_AVAILABLE:
        print("FastAPI is not installed. Please install fastapi and uvicorn to run the agent server.")
        return
    import uvicorn
    uvicorn.run(app, host=config.SERVER_HOST, port=config.SERVER_PORT)


if __name__ == "__main__":
    main()
