import logging
from typing import Any

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

from .shared import (
    set_current_customer_no,
    reset_current_customer_no,
    report_risk_event,
    add_blacklist,
)

logger = logging.getLogger(__name__)


class ActionReportRiskEvent(Action):
    name = "action_report_risk_event"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            event_type = action_kwargs.get("event_type", "")
            event_level = action_kwargs.get("event_level", "medium")
            customer_no = action_kwargs.get("customer_no")
            contract_no = action_kwargs.get("contract_no")
            result = await report_risk_event(
                event_type=event_type,
                event_level=event_level,
                customer_no=customer_no,
                contract_no=contract_no,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="风险事件上报成功")])
            else:
                return ActionResult(messages=[BotMessage(text="风险事件上报失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionAddBlacklist(Action):
    name = "action_add_blacklist"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            blacklist_type = action_kwargs.get("blacklist_type", "")
            customer_no = action_kwargs.get("customer_no")
            result = await add_blacklist(
                blacklist_type=blacklist_type,
                customer_no=customer_no,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="黑名单添加成功")])
            else:
                return ActionResult(messages=[BotMessage(text="黑名单添加失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)