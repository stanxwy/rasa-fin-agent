from typing import Any

from pydantic import BaseModel

from agent.domain.state import DialogueState
from agent.task.action.base import ActionResult
from agent.task.action.registry import ActionRegistry


class ActionCall(BaseModel):
    """
    A request to invoke a concrete action.

    Encapsulates *which* action to execute and *what* arguments to pass.
    Typically constructed by the FlowExecutor in upstream steps.

    Attributes:
        action_name: The unique name of the action registered in ActionRegistry.
        action_kwargs: Arbitrary keyword arguments passed to the action's run method.
    """
    action_name: str
    action_kwargs: dict[str, Any] = {}


class ActionRunner:
    """
    Executes actions in a unified, extensible way.

    This class follows the Open-Closed Principle (OCP):
    - Closed for modification (core execution logic stays stable).
    - Open for extension (new actions are added via ActionRegistry).

    Responsibilities:
    1. Look up an action implementation by name.
    2. Dispatch execution to the resolved action.
    3. Return the standardized ActionResult.

    It does **not** know:
    - What the action does internally.
    - How the action is implemented.

    The FlowExecutor is expected to construct ActionCall objects and delegate
    execution to this runner.
    """

    def __init__(self, registry: ActionRegistry) -> None:
        self.registry = registry

    async def run(self, action_call: ActionCall, state: DialogueState) -> ActionResult:
        action_name = action_call.action_name

        action = self.registry.get(action_name)

        return await action.run(state, action_call.action_kwargs)