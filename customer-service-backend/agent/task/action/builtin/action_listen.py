# agent/task/action/builtin/action_listen.py
import asyncio
import logging
from typing import Any

from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

logger = logging.getLogger(__name__)

class ActionListen(Action):

    name = "action_listen"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        logger.info(f"[{state.current_session_id}] waiting for user input...")
        return ActionResult()