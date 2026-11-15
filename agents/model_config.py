import os


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


def get_agent_model(agent_env_prefix: str) -> str:
    """
    Resolve model name for an agent from environment.

    Priority:
    1. <AGENT_ENV_PREFIX>_MODEL (for example, INTAKE_AGENT_MODEL)
    2. GROQ_MODEL (shared model for all agents)
    3. DEFAULT_GROQ_MODEL
    """
    prefix = (agent_env_prefix or "").strip().upper()
    if prefix:
        specific_model = os.getenv(f"{prefix}_MODEL", "").strip()
        if specific_model:
            return specific_model

    shared_model = os.getenv("GROQ_MODEL", "").strip()
    if shared_model:
        return shared_model

    return DEFAULT_GROQ_MODEL
