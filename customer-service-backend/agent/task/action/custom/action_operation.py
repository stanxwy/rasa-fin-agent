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


class ActionCreateSupportTicket(Action):
    name = "action_create_support_ticket"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            customer_no = action_kwargs.get("customer_no", "")
            ticket_type = action_kwargs.get("ticket_type", "complaint")
            content = action_kwargs.get("content", "")
            result = await create_support_ticket(
                customer_no=customer_no,
                ticket_type=ticket_type,
                content=content,
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
            customer_no = action_kwargs.get("customer_no", "")
            notification_type = action_kwargs.get("notification_type", "system")
            content = action_kwargs.get("content", "")
            result = await send_notification(
                customer_no=customer_no,
                notification_type=notification_type,
                content=content,
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
            workflow_type = action_kwargs.get("workflow_type", "")
            result = await create_workflow_instance(
                workflow_type=workflow_type,
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