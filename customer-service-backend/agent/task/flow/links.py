from pydantic import BaseModel


class FlowStepLink(BaseModel):
    target: str


class StaticLink(FlowStepLink):
    ...


class ConditionalLink(FlowStepLink):
    """
    if condition:
    """
    condition: str


class FallbackLink(FlowStepLink):
    """
    else condition:
    """