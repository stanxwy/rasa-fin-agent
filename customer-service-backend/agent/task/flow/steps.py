from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel

from agent.task.flow.links import (
    ConditionalLink,
    FallbackLink,
    FlowStepLink,
    StaticLink,
)


class ResponseDefinition(BaseModel):
    mode: Literal["static", "rephrase"] = "static"
    text: str                   # required field
    prompt: str | None = None   # prompt for LLM when model==rephrase


class FlowStepType(StrEnum):
    START = "start"
    END = "end"
    ACTION = "action"
    COLLECT = "collect"


class FlowStep(BaseModel):
    id: str
    type: FlowStepType
    next: list[FlowStepLink] = []
    description: str = ""

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "FlowStep":
        step_type = step_data['type']
        clz = STEP_TYPE_TO_CLASS[step_type]
        return clz.from_dict(step_data)

    @staticmethod
    def base_fields(base_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": base_data['id'],
            "type": FlowStepType(base_data['type']),
            "description": base_data.get('description', ''),
            "next": FlowStep.build_links(base_data['next'])
        }

    @staticmethod
    def build_links(link_data: str | list[dict[str, Any]]) -> list[FlowStepLink]:
        if isinstance(link_data, str):
            return [StaticLink(target=link_data)]
        
        elif isinstance(link_data, list):
            links = []
            for link_dict in link_data:
                if "if" in link_dict:
                    links.append(ConditionalLink(condition=link_dict['if'], target=link_dict['then']))
                else:
                    links.append(FallbackLink(target=link_dict['else']))
            return links
        elif link_data is None:
            return []
        else:
            raise ValueError(f"Invalid link data: {link_data}")


class StartFlowStep(FlowStep):
    type: FlowStepType = FlowStepType.START

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "StartFlowStep":
        return cls(**FlowStep.base_fields(step_data))


class EndFlowStep(FlowStep):
    type: FlowStepType = FlowStepType.END

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "EndFlowStep":
        return cls(**FlowStep.base_fields(step_data))


class ActionFlowStep(FlowStep):
    type: FlowStepType = FlowStepType.ACTION
    # 合法 action 名由 ActionRegistry（Action 子类的 name）单一真源决定，
    # 这里不再硬编码清单；加载期由 validate_flow_actions 统一校验。
    action: str
    args: dict | str = {}

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "ActionFlowStep":
        return cls(**FlowStep.base_fields(step_data),
                   action=step_data['action'],
                   args=step_data.get('args', {}))


class CollectFlowStep(FlowStep):
    type: FlowStepType = FlowStepType.COLLECT
    slot_name: str
    response: ResponseDefinition

    @classmethod
    def from_dict(cls, step_data: dict[str, Any]) -> "CollectFlowStep":
        return cls(
            **FlowStep.base_fields(step_data),
            slot_name=step_data['slot_name'],
            response=ResponseDefinition(**step_data['response'])
        )


# dynamic dispatch via dict lookup
STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "action": ActionFlowStep,
    "collect": CollectFlowStep,
    "end": EndFlowStep
}
