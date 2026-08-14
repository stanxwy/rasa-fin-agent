import logging
from datetime import date
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


def _slots(state: DialogueState) -> dict[str, Any]:
    return state.active_task.slots if state.active_task else {}


class ActionReportRiskEvent(Action):
    name = "action_report_risk_event"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            event_type = s.get("event_type", action_kwargs.get("event_type", ""))
            risk_score = int(s.get("risk_score", action_kwargs.get("risk_score", 0)) or 0)
            customer_no = s.get("customer_no", state.sender_id)
            related_type = s.get("related_type", action_kwargs.get("related_type", "customer"))
            related_id = s.get("related_id", action_kwargs.get("related_id"))
            result = await report_risk_event(
                event_type=event_type,
                risk_score=risk_score,
                customer_no=customer_no,
                related_type=related_type,
                related_id=related_id,
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
            s = _slots(state)
            subject_type = s.get("subject_type", s.get("blacklist_type", action_kwargs.get("subject_type", "")))
            subject_value = s.get("subject_value", s.get("customer_no", action_kwargs.get("subject_value", state.sender_id)))
            risk_level_code = s.get("risk_level_code", action_kwargs.get("risk_level_code", "R3"))
            reason = s.get("reason", action_kwargs.get("reason", ""))
            effective_from = s.get("effective_from", action_kwargs.get("effective_from", date.today().isoformat()))
            result = await add_blacklist(
                subject_type=subject_type,
                subject_value=subject_value,
                risk_level_code=risk_level_code,
                reason=reason,
                effective_from=effective_from,
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
