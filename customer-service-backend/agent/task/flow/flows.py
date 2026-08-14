from pydantic import BaseModel

from agent.task.flow.steps import CollectFlowStep, FlowStep, StartFlowStep


class FlowSlot(BaseModel):
    name: str
    type: str = "any"
    label: str = ""
    description: str = ""


class Flow(BaseModel):
    id: str
    description: str = ""
    steps: list[FlowStep] = []
    slots: list[FlowSlot] = []
    name: str | None = None

    @property
    def collect_step_slot_names(self) -> frozenset[str]:
        return frozenset(
            s.slot_name for s in self.steps
            if isinstance(s, CollectFlowStep)
        )

    def start_step(self) -> StartFlowStep | None:
        for step in self.steps:
            if isinstance(step, StartFlowStep):
                return step
        return None

    def get_step_by_id(self, step_id: str) -> FlowStep | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None


class FlowsList(BaseModel):
    flows: list[Flow] = []
    slots: dict[str, FlowSlot] = {}

    def get_flow_by_id(self, flow_id: str) -> Flow | None:
        for flow in self.flows:
            if flow.id == flow_id:
                return flow
        return None

    def get_readable_flow_name(self, flow_id) -> str:
        flow = self.get_flow_by_id(flow_id)
        return flow.name if flow else flow_id