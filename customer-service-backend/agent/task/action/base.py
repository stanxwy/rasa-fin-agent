from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState


class ActionResult(BaseModel):
    messages: list[BotMessage] = []
    slot_updates: dict[str, Any] = {}


class Action(ABC):
    name: str

    @abstractmethod
    async def run(
        self,
        state: DialogueState,
        action_kwargs: dict[str, Any],
    ) -> ActionResult:
        ...