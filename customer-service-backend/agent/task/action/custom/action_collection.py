import logging
from typing import Any

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

from .shared import (
    set_current_customer_no,
    reset_current_customer_no,
    create_collection_case,
    add_collection_action,
)

logger = logging.getLogger(__name__)


def _slots(state: DialogueState) -> dict[str, Any]:
    return state.active_task.slots if state.active_task else {}


class ActionCreateCollectionCase(Action):
    name = "action_create_collection_case"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            overdue_no = s.get("overdue_no", s.get("customer_no", action_kwargs.get("overdue_no", state.sender_id)))
            collector_no = s.get("collector_no", action_kwargs.get("collector_no", ""))
            collection_stage = s.get("collection_stage", s.get("case_type", action_kwargs.get("collection_stage", "overdue")))
            result = await create_collection_case(
                overdue_no=overdue_no,
                collector_no=collector_no,
                collection_stage=collection_stage,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="催收案件创建成功")])
            else:
                return ActionResult(messages=[BotMessage(text="催收案件创建失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionAddCollectionAction(Action):
    name = "action_add_collection_action"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            case_no = s.get("case_no", action_kwargs.get("case_no", ""))
            action_type = s.get("collection_action_type", s.get("action_type", action_kwargs.get("action_type", "phone_call")))
            action_result = s.get("action_result", action_kwargs.get("action_result", "pending"))
            result = await add_collection_action(
                case_no=case_no,
                action_type=action_type,
                action_result=action_result,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="催收行动添加成功")])
            else:
                return ActionResult(messages=[BotMessage(text="催收行动添加失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)
