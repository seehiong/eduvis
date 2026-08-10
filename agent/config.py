"""
Configuration settings for EduVis Agent server and model orchestration.
"""

import os

class AgentConfig:
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Model ladder definitions
    MODEL_FAST: str = os.getenv("EDUVIS_MODEL_FAST", "qwen3.5:4b")
    MODEL_DEFAULT: str = os.getenv("EDUVIS_MODEL_DEFAULT", "qwen3.5:9b")
    MODEL_HEAVY: str = os.getenv("EDUVIS_MODEL_HEAVY", "qwen3.5:27b")

    MAX_CRITIQUE_RETRIES: int = int(os.getenv("EDUVIS_MAX_CRITIQUE_RETRIES", "3"))
    SERVER_HOST: str = os.getenv("EDUVIS_AGENT_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("EDUVIS_AGENT_PORT", "8000"))

config = AgentConfig()
