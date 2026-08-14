import logging
from collections.abc import Callable
from typing import Any

from langchain_core.runnables import RunnableLambda

logger = logging.getLogger(__name__)

def log_prompt_stage(
    *,
    level: str = "INFO",
    message: str = "Prompt:",
    when: str = "invoke",  # "invoke" | "stream" | "both"
    enabled: bool = True,
) -> Callable[[Any], Any]:
    """
    Returns a LangChain-compatible operator that logs prompt inputs.

    Usage:
        chain = prompt | log_prompt_stage() | llm

    Why this exists:
    - Avoids lambda + tuple hacks
    - Centralizes prompt observability
    - Makes logging configurable and testable
    """
    if not enabled:
        return RunnableLambda(lambda x: x)

    log = getattr(logger, level.lower())

    def _log(x: Any) -> Any:
        log(message)

        if hasattr(x, "text") and isinstance(x.text, str):
            log(x.text)
        return x
    return RunnableLambda(_log)


def log_llm_response(
    *,
    level: str = "INFO",
    message: str = "LLM Response:",
    enabled: bool = True,
) -> Callable[[Any], Any]:

    if not enabled:
        return RunnableLambda(lambda x: x)

    log = getattr(logger, level.lower())

    def _log(x: Any) -> Any:
        log(message)

        if hasattr(x, "content") and isinstance(x.content, str):
            log(x.content)

        if isinstance(x, str):
            log(x)
        return x
    return RunnableLambda(_log)
