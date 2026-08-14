import logging
from typing import Any

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

from .shared import (
    set_current_customer_no,
    reset_current_customer_no,
    create_support_ticket,
    send_notification,
    create_workflow_instance,
)

logger = logging.getLogger(__name__)


def _slots(state: DialogueState) -> dict[str, Any]:
    return state.active_task.slots if state.active_task else {}


class ActionCreateSupportTicket(Action):
    name = "action_create_support_ticket"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            customer_no = s.get("customer_no", state.sender_id)
            ticket_type = s.get("ticket_type", action_kwargs.get("ticket_type", "complaint"))
            ticket_title = s.get("ticket_title", action_kwargs.get("ticket_title", ""))
            ticket_content = s.get("ticket_content", s.get("content", action_kwargs.get("ticket_content", "")))
            related_type = s.get("related_type", action_kwargs.get("related_type", "none"))
            result = await create_support_ticket(
                customer_no=customer_no,
                ticket_type=ticket_type,
                ticket_title=ticket_title,
                ticket_content=ticket_content,
                related_type=related_type,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="工单创建成功")])
            else:
                return ActionResult(messages=[BotMessage(text="工单创建失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionSendNotification(Action):
    name = "action_send_notification"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            customer_no = s.get("customer_no", state.sender_id)
            message_type = s.get("message_type", s.get("notification_type", action_kwargs.get("message_type", "system")))
            send_channel = s.get("send_channel", action_kwargs.get("send_channel", "app"))
            related_type = s.get("related_type", action_kwargs.get("related_type", "none"))
            message_title = s.get("message_title", action_kwargs.get("message_title", ""))
            message_content = s.get("message_content", s.get("notification_content", s.get("content", action_kwargs.get("message_content", ""))))
            result = await send_notification(
                customer_no=customer_no,
                message_type=message_type,
                send_channel=send_channel,
                related_type=related_type,
                message_title=message_title,
                message_content=message_content,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="通知发送成功")])
            else:
                return ActionResult(messages=[BotMessage(text="通知发送失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionCreateWorkflowInstance(Action):
    name = "action_create_workflow_instance"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            workflow_type = s.get("workflow_type", action_kwargs.get("workflow_type", ""))
            related_type = s.get("related_type", action_kwargs.get("related_type", "none"))
            related_id = int(s.get("related_id", action_kwargs.get("related_id", 0)) or 0)
            initiator_type = s.get("initiator_type", action_kwargs.get("initiator_type", "customer"))
            initiator_no = s.get("initiator_no", action_kwargs.get("initiator_no", state.sender_id))
            result = await create_workflow_instance(
                workflow_type=workflow_type,
                related_type=related_type,
                related_id=related_id,
                initiator_type=initiator_type,
                initiator_no=initiator_no,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="工作流实例创建成功")])
            else:
                return ActionResult(messages=[BotMessage(text="工作流实例创建失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)
