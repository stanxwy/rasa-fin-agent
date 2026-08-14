import logging
from datetime import date, timedelta
from typing import Any

from agent.domain.messages import BotMessage
from agent.domain.state import DialogueState
from agent.task.action.base import Action, ActionResult

from .shared import (
    set_current_customer_no,
    reset_current_customer_no,
    submit_repayment,
    create_repayment_authorization,
    submit_fee_reduction,
)

logger = logging.getLogger(__name__)


def _slots(state: DialogueState) -> dict[str, Any]:
    return state.active_task.slots if state.active_task else {}


class ActionSubmitRepayment(Action):
    name = "action_submit_repayment"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            bill_no = s.get("bill_no", s.get("contract_no", action_kwargs.get("bill_no", "")))
            account_no = s.get("account_no", action_kwargs.get("account_no", ""))
            repayment_amount = s.get("repayment_amount", s.get("amount", action_kwargs.get("repayment_amount", 0)))
            repayment_type = s.get("repayment_type", action_kwargs.get("repayment_type", "normal"))
            result = await submit_repayment(
                bill_no=bill_no,
                account_no=account_no,
                repayment_amount=repayment_amount,
                repayment_type=repayment_type,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="还款提交成功")])
            else:
                return ActionResult(messages=[BotMessage(text="还款提交失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionCreateRepaymentAuthorization(Action):
    name = "action_create_repayment_authorization"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            contract_no = s.get("contract_no", action_kwargs.get("contract_no", ""))
            account_no = s.get("account_no", action_kwargs.get("account_no", ""))
            authorization_type = s.get("authorization_type", action_kwargs.get("authorization_type", "auto_debit"))
            valid_from = s.get("valid_from", action_kwargs.get("valid_from", date.today().isoformat()))
            valid_to = s.get("valid_to", action_kwargs.get("valid_to", (date.today() + timedelta(days=365)).isoformat()))
            result = await create_repayment_authorization(
                contract_no=contract_no,
                account_no=account_no,
                authorization_type=authorization_type,
                valid_from=valid_from,
                valid_to=valid_to,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="自动还款授权创建成功")])
            else:
                return ActionResult(messages=[BotMessage(text="自动还款授权创建失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)


class ActionSubmitFeeReduction(Action):
    name = "action_submit_fee_reduction"

    async def run(self, state: DialogueState, action_kwargs: dict[str, Any]) -> ActionResult:
        token = set_current_customer_no(state.sender_id)
        try:
            s = _slots(state)
            bill_no = s.get("bill_no", s.get("contract_no", action_kwargs.get("bill_no", "")))
            reduction_type = s.get("reduction_type", action_kwargs.get("reduction_type", "penalty"))
            apply_amount = s.get("apply_amount", s.get("fee_reduction_amount", s.get("amount", action_kwargs.get("apply_amount", 0))))
            reason = s.get("fee_reduction_reason", s.get("reason", action_kwargs.get("reason", "")))
            result = await submit_fee_reduction(
                bill_no=bill_no,
                reduction_type=reduction_type,
                apply_amount=apply_amount,
                reason=reason,
            )
            if result:
                return ActionResult(messages=[BotMessage(text="费用减免申请提交成功")])
            else:
                return ActionResult(messages=[BotMessage(text="费用减免申请提交失败，请重试")])
        except Exception as e:
            logger.error(f"{self.name} failed: {e}")
            return ActionResult(messages=[BotMessage(text=f"操作异常: {e}")])
        finally:
            reset_current_customer_no(token)
